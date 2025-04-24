import { mediaUtils } from "./media_utils.js";

const vizUtils = (
    function() {

        // Constants
        const plotWidth = 700;
        const plotHeight = 500;
        const margin = {top: 30, right: 30, bottom: 30, left: 60};
        // MMIs
        const mmiDefaultColor = "rgba(0,255,0,0.2)";
        const mmiHoverColor = "rgba(0,255,0,1)";
        const mmiSelectColor = "rgba(255,50,0,1);"

        const polyline = function(T, Y, tscale, yscale) {
            return T.map((t, i) => tscale(t).toFixed(1) + "," + yscale(Y[i]).toFixed(1)).join(
                " "
            );
        }

        // Public Utilities
        /**
         * Returns the extent of a scalar data key's value
         * or step.
         * 
         * @param {Object[DataReport]} allData 
         * @param {string} key 
         * @param {Array} simIDs 
         * @param {value_or_step} dataPointAttribute 
         * @returns 
         */
        const extentOf = function(allData, key, simIDs, dataPointAttribute="value") {
            // Use all simulations if IDs is not specified
            if (simIDs === undefined) {
                simIDs = Object.keys(allData);
            }
            const extent = [Infinity, -Infinity];
            if (simIDs.length < 1) {
                return extent;
            }
            if (!allData[simIDs[0]].has(key)) {
                return extent;
            }
            // If the given key is not scalar and we are trying to find the
            // extent of it's "value", then that's not possible. We can find
            // the extent of its "step" or "wall_time", but "value" only
            // makes sense for scalars.
            if (!allData[simIDs[0]].isScalar(key) && dataPointAttribute === "value") {
                return extent;
            }
            for (const simID of simIDs) {
                const tempExt = d3.extent(allData[simID].getData(key).map(x => x[dataPointAttribute]));
                if (tempExt[0] !== undefined && tempExt[0] < extent[0]) {
                    extent[0] = tempExt[0];
                }
                if (tempExt[1] !== undefined && tempExt[1] > extent[1]) {
                    extent[1] = tempExt[1];
                }
            }
            return extent;
        }
        const getPlotOrMakeNew = function(existingSVG) {
            const width = plotWidth;
            const height = plotHeight;
            if (existingSVG === undefined) {
                existingSVG = d3
                    // .select("#plots-area")
                    // .append("svg")
                    .create("svg")
                    .attr("viewBox", `0 0 ${width} ${height}`)
                    .attr("preserveAspectRatio", "xMinYMin meet")
                    // .attr("width", width)
                    // .attr("height", height)
                    .style("border", "1px solid black");
            }
            return existingSVG;
        }
        /**
         * Creates a d3 svg line plot for the given key and given
         * data report.
         * 
         * @param {string} key
         * @param {dataReport} allData
         */
        const createLinePlotForKey = function(key, allData, svg) {
            svg = getPlotOrMakeNew(svg);

            const extentY = extentOf(allData, key, undefined, "value");
            const extentX = extentOf(allData, key, undefined, "step");

            const width = plotWidth;
            const height = plotHeight;

            const xScale = d3
                .scaleLinear()
                .domain(extentX)
                .range([margin.left, width - margin.right]);
            const yScale = d3
                .scaleLinear()
                .domain(extentY)
                .nice()
                .range([height - margin.bottom, margin.top]);

            const xAxis = svg
                .append("g")
                .attr("transform", `translate(0,${height - margin.bottom})`)
                .call(d3.axisBottom(xScale));
            const yAxis = svg
                .append("g")
                .attr("transform", `translate(${margin.left - 1}, 0)`)
                .call(d3.axisLeft(yScale));

            for (const simID in allData) {
                const data = allData[simID].getScalar(key);
                const pline = svg
                    .append("path")
                    .datum(data)
                    .attr("fill", "none")
                    .attr("stroke", "steelblue")
                    .attr("stroke-width", 1.5)
                    .attr("d", d3.line()
                        .x(d => xScale(d.step))
                        .y(d => yScale(d.value))
                    );
            }
            return svg;
        }

        const getMMIPoints = function(offset=[0,0]) {
            const sideLength = 20;

            const data = [
                [0,0],
                [-sideLength/2,Math.sqrt(3)*sideLength/2],
                [sideLength/2,Math.sqrt(3)*sideLength/2],
            ]
            return data.map((pt) => pt.map((v, idx) => v + offset[idx]));
        }
        const createMMI = function(point, svg, xScale) {
            if (svg === undefined) { return undefined; }
            const width = plotWidth;
            const height = plotHeight;
            console.log(point);
            console.log(xScale(point.step));
            const markerPoints = getMMIPoints([xScale(point.step), height-margin.bottom]);
            const markerPointsString = markerPoints.map(pt => `${pt[0]},${pt[1]}`).join(" ");
            console.log(markerPointsString);
            return svg.append("polygon")
                .attr("points", markerPointsString)
                .attr("stroke", "yellow")
                .attr("stroke-width", 1)
                .attr("fill", mmiDefaultColor);
        }
        const mouseoverMMI = function(mmi) {
            d3.select(this)
                .attr("fill", mmiHoverColor);
        }
        const mousemoveMMI = function(mmi) {
            // d3.select(this)
            //     .attr("fill", "rgba(0,255,0,1)");
        }
        const mouseleaveMMI = function(mmi) {
            d3.select(this)
                .attr("fill", mmiDefaultColor);
        }
        const clickMMI = function(mmi) {
            console.log(mmi);
            d3.select(this)
                .attr("fill", mmiSelectColor);
        }
        const addMMIs = function(key, allData, svg) {
            svg = getPlotOrMakeNew(svg);

            const width = plotWidth;
            const height = plotHeight;

            const tempID = Object.keys(allData)[0]
            let type = "images";
            // let type = undefined;
            // if (Object.hasOwn(allData[tempID].media["images"], key)) {
            //     type = "images";
            // } else if (Object.hasOwn(allData[tempID].media["audio"], key)) {
            //     type = "audio";
            // }
            // if (type === undefined) { console.error("No media key " + key); return svg; }

            // const extentY = d3.extent(y);
            // const extentX = extentOf(allData, key, undefined, "step");
            const extentX = [0, 100000];

            const xScale = d3
                .scaleLinear()
                .domain(extentX)
                .range([margin.left, width - margin.right]);

            for (const simID in allData) {
                const data = allData[simID].getData(key);
                if (data === undefined) { continue; }
                for (const point of data) {
                    createMMI(point, svg, xScale)
                        .on("mouseover", mouseoverMMI)
                        .on("mousemove", mousemoveMMI)
                        .on("mouseleave", mouseleaveMMI)
                        .on("click", clickMMI);
                }
            }
            return svg;
        }

        return {
            createLinePlotForKey,
            addMMIs,
        };
    }
)();

export { vizUtils };