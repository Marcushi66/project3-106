import * as d3 from "https://cdn.jsdelivr.net/npm/d3@7.9.0/+esm";

// Just load a simple world map outline
d3.json("https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json").then(data => {
  const countries = topojson.feature(data, data.objects.countries);
  const projection = d3.geoNaturalEarth1().fitSize([800, 400], countries);
  const path = d3.geoPath(projection);

  const svg = d3.select("#map");
  svg.selectAll("path")
    .data(countries.features)
    .join("path")
    .attr("d", path)
    .attr("fill", "#c7e9b4")
    .attr("stroke", "#555");

  // add simple text
  svg.append("text")
    .attr("x", 20)
    .attr("y", 30)
    .text("Prototype: World Map Base (NDVI coming soon)")
    .attr("font-size", "14px");
});
