
const vizUtils = (
    function() {

        // Constants
        const plotWidth = 700;
        const plotHeight = 500;
        const margin = {top: 30, right: 30, bottom: 30, left: 60};
        // MMIs
        const mmiDefaultColor = "rgba(0,255,0,0.2)";
        const mmiHoverColor = "rgba(0,255,0,1)";
        const mmiSelectColor = "rgba(255,50,0,1)";
        const mmiSideLength = 20;
        const mmiGap = 0;
        const minMMIRectWidth = 2;

        class MMIData {
            static COLOR_DEFAULT    = "rgba(0,255,0,0.2)";
            static COLOR_HOVER      = "rgba(0,255,0,1)";
            static COLOR_SELECT     = "rgba(255,50,0,1)";

            constructor() {
                this.reports = [];
                this.keys = [];
                this.steps = [];
                this.idxs = [];

                this._cachedExtent = [-Infinity, Infinity];
                this._dirtyExtent = true;
            }

            addData(simDataReport, key, step) {
                this.reports.push(simDataReport);
                this.keys.push(key);
                this.steps.push(step);
                this.idxs.push(simDataReport.getData(key).findIndex(d => d.step == step));
                debug(this);
                this._dirtyExtent = true;
            }

            getData() {
                const data = [];
                for (let i = 0; i < this.idxs.length; i++) {
                    const report = this.reports[i];
                    const key = this.keys[i];
                    const idx = this.idxs[i];
                    const datum = report.getData(key)[idx];
                    const type = report.getKeyType(key);
                    data.push(
                        {
                            simID: report.simID,
                            key: key,
                            type: type,
                            datum: datum
                        }
                    );
                }
                return data;
            }

            getStepExtent() {
                if (this._dirtyExtent) {
                    const steps = this.getData().map(d => d.datum.step);
                    this._cachedExtent = d3.extent(steps);
                    this._dirtyExtent = false;
                }
                return this._cachedExtent;
            }
        }

        class Plot {
            constructor(svg, extentX, extentY, scaleX, scaleY) {
                this.svg        = svg;
                this.extentX    = extentX;
                this.extentY    = extentY;
                this.scaleX     = scaleX;
                this.scaleY     = scaleY;

                this.onClickMMI = undefined;
                this.selectedMMI = undefined;
                this.createdMMIs = [];
            }

            updateExtentX(otherExtentOrValues) {
                this.extentX = d3.extent([...otherExtentOrValues, ...this.extentX]);
            }
            updateExtentY(otherExtentOrValues) {
                this.extentY = d3.extent([...otherExtentOrValues, ...this.extentY]);
            }

            #addMMIRect() {
                const height = plotHeight;
                this.mmiExtentRect = this.svg
                    .append("rect")
                    .attr("x", margin.left)
                    .attr("width", minMMIRectWidth)
                    .attr("y", margin.top)
                    .attr("height", height - margin.top - margin.bottom)
                    .style("fill", "darkorange")
                    .style("opacity", 0.4);
            }

            mousemoveMMI(mmi) {
                // d3.select(this)
                //     .attr("fill", "rgba(0,255,0,1)");
            }
            mouseoverMMI(mmi) {
                const mmiSelection = d3.select(mmi.target);
                const mmiData = mmiSelection.data()[0];
                // Update MMI extent rectangle
                if (this.mmiExtentRect) {
                    const extent = mmiData.getStepExtent();
                    const rectWidth = Math.max(minMMIRectWidth, this.scaleX(extent[1]) - this.scaleX(extent[0]));
                    this.mmiExtentRect
                        .attr("x", this.scaleX(extent[0]))
                        .attr("width", rectWidth);
                }
                // Maybe change the MMI color
                if (this.selectedMMI === mmi.target) { return; }
                if (!mmiData) { return; }
                mmiSelection
                    .attr("fill", mmiHoverColor);
            }
            mouseleaveMMI(mmi) {
                const mmiSelection = d3.select(mmi.target);
                if (this.selectedMMI === mmi.target) { return; }
                mmiSelection
                    .attr("fill", mmiDefaultColor);
            }
            clickMMI(mmi) {
                if (this.selectedMMI && this.selectedMMI !== mmi.target) {
                    d3.select(this.selectedMMI).attr("fill", mmiDefaultColor);
                }
                this.selectedMMI = mmi.target;
                debug(this.selectedMMI);
                d3.select(this.selectedMMI)
                    .attr("fill", mmiSelectColor);

                if (this.onClickMMI) {
                    this.onClickMMI(mmi);
                }
            }

            addAllMMIs(allData, onclick, condense=true) {
                const mediaKeys = new Set();
                for (const simID in allData) {
                    allData[simID].getMediaKeys().forEach(mediaKeys.add, mediaKeys);
                }
                debug("mediaKeys");
                debug(mediaKeys);
                const createdMMIs = this.createdMMIs;
                for (const key of mediaKeys) {
                    this.addMMIs(key, allData, onclick, condense, createdMMIs);
                }

                this.#addMMIRect();
            }
            addMMIs(key, allData, onclick, condense=true, createdMMIs=[]) {
                const width = plotWidth;
                const height = plotHeight;
    
                const extentX = this.extentX;
                const xScale = this.scaleX;
    
                for (const simID in allData) {
                    const data = allData[simID].getData(key);
                    if (data === undefined) { continue; }
                    for (const point of data) {
                        // Check if this point would be too close to an existing
                        // MMI. If so, then get that MMI's MMIData and add this
                        // point's data to it.
                        const closestMMIIdx = d3.bisectCenter(createdMMIs.map(d => d.step), point.step);
                        debug(closestMMIIdx);
                        // Check the difference in step value and convert to actual length.
                        // Compare against the width of MMI markers
                        if (closestMMIIdx >= 0 && closestMMIIdx < createdMMIs.length) {
                            debug("step difference: " + Math.abs(createdMMIs[closestMMIIdx].step - point.step) + ". scale difference: " + Math.abs(xScale(createdMMIs[closestMMIIdx].step) - xScale(point.step)));
                        }
                        if (
                            condense &&
                            closestMMIIdx >= 0 &&
                            closestMMIIdx < createdMMIs.length &&
                            Math.abs(xScale(createdMMIs[closestMMIIdx].step) - xScale(point.step)) < (mmiSideLength+mmiGap)
                        ) {
                            createdMMIs[closestMMIIdx].selection.data()[0].addData(allData[simID], key, point.step);
                        }
                        else {
                            const markerPoints = getMMIPoints([xScale(point.step), height-margin.bottom]);
                            const mmiData = new MMIData();
                            mmiData.addData(allData[simID], key, point.step);
                            this.onClickMMI = onclick;
                            const mmi = createMMI(this.svg, markerPoints)
                                .data([mmiData])
                                .on("mouseover", this.mouseoverMMI.bind(this))
                                .on("mousemove", this.mousemoveMMI.bind(this))
                                .on("mouseleave", this.mouseleaveMMI.bind(this))
                                .on("click", this.clickMMI.bind(this));
                            const created = {step: point.step, selection: mmi};
                            const insertIdx = sortedIndex(createdMMIs, created, (x) => x.step);
                            createdMMIs.splice(insertIdx, 0, created);
                        }
                    }
                }
                return createdMMIs;
            }
        }

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
            const extentX = d3.extent([...extentOf(allData, key, undefined, "step"), 0]);

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
                .attr("transform", `translate(${margin.left}, 0)`)
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
            return new Plot(
                svg,
                extentX, 
                extentY,
                xScale,
                yScale
            );
            // return svg;
        }

        const getMMIPoints = function(offset=[0,0]) {
            const data = [
                [0,0],
                [-mmiSideLength/2,Math.sqrt(3)*mmiSideLength/2],
                [mmiSideLength/2,Math.sqrt(3)*mmiSideLength/2],
            ]
            return data.map((pt) => pt.map((v, idx) => v + offset[idx]));
        }
        const createMMI = function(svg, markerPoints) {
            if (svg === undefined) { return undefined; }
            const markerPointsString = markerPoints.map(pt => `${pt[0]},${pt[1]}`).join(" ");
            return svg.append("polygon")
                .attr("points", markerPointsString)
                .attr("stroke", "yellow")
                .attr("stroke-width", 1)
                .attr("fill", mmiDefaultColor);
        }

        return {
            createLinePlotForKey,
        };
    }
)();

export { vizUtils };