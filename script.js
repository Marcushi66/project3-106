// script.js
import * as d3 from "https://cdn.jsdelivr.net/npm/d3@7.9.0/+esm";

const svg = d3.select("#world");
const g = svg.append("g");

const projection = d3.geoNaturalEarth1()
  .scale(190)
  .translate([490, 270]);

const path = d3.geoPath(projection);

const zoom = d3.zoom()
  .scaleExtent([1, 8])
  .on("zoom", e => g.attr("transform", e.transform));

svg.call(zoom);

// -------- load data --------
const monthNames = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
const monthInput = document.getElementById("month");
const monthLabel = document.getElementById("monthLabel");
const tooltip = d3.select("#tooltip");

const color = d3.scaleSequential(d3.interpolateGreens).domain([0.10, 0.85]);
const noData = "#2a355d";

const [worldGeo, raw] = await Promise.all([
  d3.json("https://raw.githubusercontent.com/holtzy/D3-graph-gallery/master/DATA/world.geojson"),
  d3.csv("data/ndvi_country_2024_clean.csv", d3.autoType)
]);

const data = raw.filter(d => /^[A-Z]{3}$/.test(d.iso3) && d.month >= 1 && d.month <= 12);

const byIso = d3.group(data, d => d.iso3);
const ndviByIsoMonth = new Map(
  [...byIso].map(([iso, rows]) => {
    const arr = Array(12).fill(null);
    rows.forEach(r => { arr[r.month - 1] = r.ndvi_mean; });
    return [iso, arr];
  })
);

// -------- prepare country features --------
const countries = worldGeo.features;

// Helper to get ISO3 code from country feature
function getISO3(f) {
  return f.id;
}

// -------- draw countries --------
const countryPaths = g.selectAll("path.country")
  .data(countries)
  .join("path")
  .attr("class", "country")
  .attr("d", path)
  .attr("fill", f => {
    const iso = getISO3(f);
    const series = ndviByIsoMonth.get(iso);
    const v = series ? series[+monthInput.value - 1] : null;
    return v == null ? noData : color(v);
  })
  .attr("stroke", "#1e2a4f")
  .attr("stroke-width", 0.6)
  .on("mousemove", (e, d) => {
    const iso = getISO3(d);
    const mIdx = +monthInput.value - 1;
    const series = ndviByIsoMonth.get(iso);
    const val = series ? series[mIdx] : null;

    tooltip.html(
      `<strong>${d.properties.name}</strong><br>` +
      `NDVI: ${val == null ? "No data" : val.toFixed(3)}<br>` +
      `${monthNames[mIdx]}`
    )
      .style("left", (e.clientX + 12) + "px")
      .style("top", (e.clientY - 12) + "px")
      .style("opacity", 1);
  })
  .on("mouseleave", () => tooltip.style("opacity", 0))
  .on("click", (e, d) => showTrend(d));

// -------- month input --------
monthInput.addEventListener("input", updateColors);

// -------- update colors function --------
function updateColors() {
  const mIdx = +monthInput.value - 1;
  monthLabel.textContent = monthNames[mIdx];

  countryPaths.transition()
    .duration(350)
    .attr("fill", f => {
      const iso = getISO3(f);
      const series = ndviByIsoMonth.get(iso);
      const v = series ? series[mIdx] : null;
      return v == null ? noData : color(v);
    });
}

updateColors();

// -------- mini line chart --------
const mini = d3.select("#miniChart");
const mw = +mini.attr("width");
const mh = +mini.attr("height");

const mx = d3.scaleLinear().domain([1, 12]).range([30, mw - 10]);
const my = d3.scaleLinear().domain([0, 1]).range([mh - 20, 20]);

const line = d3.line()
  .defined(d => d != null)
  .x((d, i) => mx(i + 1))
  .y(d => my(d));

// -------- show trend function --------
function showTrend(f) {
  const iso = getISO3(f);
  const series = ndviByIsoMonth.get(iso);
  const asideTitle = document.getElementById("asideTitle");
  const info = document.getElementById("asideInfo");

  mini.selectAll("*").remove();

  if (!series) {
    asideTitle.textContent = f.properties.name;
    info.innerHTML = "<li>No data available</li>";
    mini.style("display", "none"); 
    return;
  }

  asideTitle.textContent = `${f.properties.name} (${iso})`;
  info.innerHTML = `<li>Average NDVI: ${(d3.mean(series) || 0).toFixed(3)}</li>`;

  mini.style("display", "block");

  // Draw axes and line
  mini.append("g")
    .attr("transform", `translate(0,${mh - 20})`)
    .call(
      d3.axisBottom(mx)
        .ticks(12)
        .tickFormat((d, i) => monthNames[i])
        .tickSize(0)
    )
    .selectAll("text")
    .attr("transform", "rotate(-45)")
    .attr("x", -10)
    .attr("y", 10);

  mini.append("g")
    .attr("transform", "translate(30,0)")
    .call(d3.axisLeft(my).ticks(5));
  mini.append("path")
    .datum(series)
    .attr("d", line)
    .attr("stroke", "#7cc77c")
    .attr("fill", "none")
    .attr("stroke-width", 2);

  mini.selectAll("circle")
    .data(series)
    .join("circle")
    .attr("cx", (d, i) => mx(i + 1))
    .attr("cy", d => my(d))
    .attr("r", 2.5)
    .attr("fill", "#7cc77c");
}

// -------- Debug: missing countries --------
(function debugMissing(){
  const missing = [];
  for (const f of countries) {
    const iso = getISO3(f);
    if (!iso || !ndviByIsoMonth.has(iso)) {
      missing.push(`${f.properties.name} (${iso})`);
    }
  }
  console.log("[NDVI] Missing or unmatched countries:", missing);
})();
