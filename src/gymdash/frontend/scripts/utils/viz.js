
const vizUtils = (
    function() {

        // Constants
        const plotWidth = 700;
        const plotHeight = 500;
        const margin = {top: 30, right: 30, bottom: 30, left: 60};
        const mmiExtentMarginPercent = 0.05;
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

                this.brushX = undefined;
                this.brushY = undefined;

                this._cachedExtent = [-Infinity, Infinity];
                this._dirtyExtent = true;
            }

            addData(simDataReport, key, step) {
                this.reports.push(simDataReport);
                this.keys.push(key);
                this.steps.push(step);
                this.idxs.push(simDataReport.getData(key).findIndex(d => d.step == step));
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

            /**
             * Return the extent of the steps of all the
             * media data in this MMI.
             * 
             * @returns Step Extent Array
             */
            getStepExtent() {
                if (this._dirtyExtent) {
                    const steps = this.getData().map(d => d.datum.step);
                    this._cachedExtent = d3.extent(steps);
                    this._dirtyExtent = false;
                }
                return this._cachedExtent;
            }
        }

        // Adapted from https://observablehq.com/@d3/learn-d3-interaction
        class Tooltip {
            constructor(svg) {
                this.svg = svg;
                
                this.node = svg.append("g")
                    .attr("pointer-events", "none")
                    .attr("display", "none")
                    .attr("font-family", "sans-serif")
                    .attr("font-size", "0.5em")
                    .attr("text-anchor", "middle");
                this.node.append("rect")
                    .attr("x", "-27")
                    .attr("y", "-30")
                    .attr("width", "54")
                    .attr("height", "20")
                    .attr("fill", "white");
                this._date = this.node.append("text")
                    .attr("y", "-22");
                this._close = this.node.append("text")
                    .attr("y", "-12");
                this.node.append("circle")
                    .attr("r", "2.5")
                    .attr("fill", "orange");
            }
            show(d) {
                this.node.attr("display", null);
                this._date.text(d.step);
                this._close.text(d.value.toFixed(2));
            }
            moveTo(newPoint) {
                this.node.attr("transform", `translate(${newPoint[0]},${newPoint[1]})`);
            }
            hide() {
                this.node.attr("display", "none");
            }
        }

        class Plot {
            constructor(svg, data, key, extentX, extentY, scaleX, scaleY, axisX, axisY, lines) {
                this.svg        = svg;
                this.data       = data;
                this.key        = key;
                this.extentX    = extentX;
                this.extentY    = extentY;
                this.scaleX     = scaleX;
                this.scaleY     = scaleY;
                this.axisX      = axisX;
                this.axisY      = axisY;
                this.lines      = lines;

                this.tooltip = new Tooltip(this.svg);

                this.onClickMMI = undefined;
                this.selectedMMI = undefined;
                this.lastHoveredMMI = undefined;
                this.createdMMIs = [];

                this.init();
            }

            #svgSize() {
                const box = this.svg.node().getBoundingClientRect();
                return {width: box.width, height: box.height};
            }

            #rebuildLines() {
                const sx = this.scaleX;
                const sy = this.scaleY;
                for (const line of this.lines) {
                    line
                        .attr("d", d3.line()
                            .x(function(d) { return sx(d.step) })
                            .y(function(d) { return sy(d.value) })
                        );
                }
            }

            #onhover(event) {
                const width = plotWidth;
                const height = plotHeight;
                
                if (this.lines.length < 1) { return; }
                // We have to scale the absolute pointer offset values by
                // the size of the svg because it can change in size.
                const offsetX = event.offsetX * (width/this.#svgSize().width);
                const offsetY = event.offsetY * (height/this.#svgSize().height);
                // Figure out which line has closest value to mouse position
                const estStep = this.scaleX.invert(offsetX);
                let finalLine;
                let dataPoint;
                let nearestDistance = Infinity;
                const neighborhood = 10;
                // Look for the nearest point on any lines.
                for (const line of this.lines) {
                    // First filter just by step value (only within certain number of steps).
                    const lineData = line.data()[0];
                    const idxStep = d3.bisectCenter(lineData.map(d => d.step), estStep);
                    // Look on either side of point in neighborhood
                    for (let i = -neighborhood; i <= neighborhood; i++) {
                        const tempPoint = lineData[idxStep+i];
                        if (!tempPoint) { continue; }
                        // Calculate pixel distance to point.
                        const xDistPixel = Math.abs(offsetX - this.scaleX(tempPoint.step));
                        const yDistPixel = Math.abs(offsetY - this.scaleY(tempPoint.value));
                        const dist = Math.sqrt(Math.pow(xDistPixel,2) + Math.pow(yDistPixel,2));
                        // Track closest line/point so far
                        if (dist < nearestDistance) {
                            nearestDistance = dist;
                            finalLine = line;
                            dataPoint = tempPoint;
                        }
                    }
                }
                if (dataPoint) {
                    this.tooltip.show(dataPoint);
                    this.tooltip.moveTo([this.scaleX(dataPoint.step), this.scaleY(dataPoint.value)]);
                }
            }
            #onleave(event) {
                this.tooltip.hide();
            }

            init() {
                const width = plotWidth;
                const height = plotHeight;
                console.log("INIT");
                // https://developer.mozilla.org/en-US/docs/Web/API/Element#mouse_events
                this.svg
                    .on("mousemove", this.#onhover.bind(this));
                this.svg
                    .on("mouseleave", this.#onleave.bind(this));

                // Brushing
                this.brushX = d3.brushX()
                    .extent([[margin.left, margin.bottom], [width, height-margin.bottom]]);
                this.svg.append("g").attr("class", "brush").call(
                    this.brushX
                );

                // Double click reset
                this.svg.on("dblclick", this.refresh.bind(this));

                // MMI highlight rectangle
                this.#addMMIRect();

                // this.svg.append(this.tooltip.node);
            }

            /**
             * Refreshes the Plot display using the updated
             * data value. Usually, the data Object will be
             * altered externally from some other activity,
             * and refresh() will update the Plot to match.
             */
            refresh() {
                // Rebuild the axes
                const extentY = extentOf(this.data, this.key, undefined, "value");
                const extentX = d3.extent([...extentOf(this.data, this.key, undefined, "step"), 0]);
                this.scaleX
                    .domain(extentX);
                this.scaleY
                    .domain(extentY);
                this.axisX
                    .call(d3.axisBottom(this.scaleX));
                this.axisY
                    .call(d3.axisLeft(this.scaleY));
                // Rebuild the lines
                this.#rebuildLines();

                this.clearMMIs();
                this.addAllMMIs(this.data, this.onClickMMI, true);
            }

            updateExtentX(otherExtentOrValues) {
                this.extentX = d3.extent([...otherExtentOrValues, ...this.extentX]);
            }
            updateExtentY(otherExtentOrValues) {
                this.extentY = d3.extent([...otherExtentOrValues, ...this.extentY]);
            }

            clearBrush() {
                this.svg.select(".brush").call(
                    this.brushX.move, null
                );
            }

            addBrushX(onbrush, eventType="end") {
                const width = plotWidth;
                const height = plotHeight;

                // if (!this.brushX) {
                //     this.brushX = d3.brushX()
                //         .extent([[margin.left, margin.bottom], [width, height-margin.bottom]])
                //     this.svg.on("dblclick", this.refresh.bind(this));
                //     this.svg.append("g").attr("class", "brush").call(
                //         this.brushX
                //     );
                // }
                // this.brushX = this.brushX
                //     .on(eventType, onbrush);

                // this.brushX = d3.brushX()
                //     .extent([[margin.left, margin.bottom], [width, height-margin.bottom]])
                this.brushX = this.brushX.on(eventType, onbrush);
            }
            updatePlot(event, otherPlot) {
                if (!event) { return; }
                const extent = event.selection;
                const scaleX = otherPlot.scaleX;
                if (!extent) { return; }
                this.updatePlotX([scaleX.invert(extent[0]), scaleX.invert(extent[1])]);
                // this.scaleX.domain([scaleX.invert(extent[0]), scaleX.invert(extent[1])]);
                // this.axisX.call(d3.axisBottom(this.scaleX));
                // this.#rebuildLines();
                // this.clearMMIs();
                // this.addAllMMIs(this.data, this.onClickMMI, true);
            }
            updatePlotX(extentX) {
                this.scaleX.domain(extentX);
                this.axisX.call(d3.axisBottom(this.scaleX));
                this.#rebuildLines();
                this.clearMMIs();
                this.addAllMMIs(this.data, this.onClickMMI, true);
            }

            #addMMIRect() {
                const height = plotHeight;
                this.mmiExtentRect = this.svg
                    .append("rect")
                    .attr("x", margin.left)
                    .attr("width", minMMIRectWidth)
                    .attr("y", margin.top)
                    .attr("height", height - margin.top - margin.bottom)
                    // .attr("pointer-events", "none")
                    .style("fill", "darkorange")
                    .style("opacity", 0.4)
                    .on("click", function(event) {
                        console.log("click mmi rect");
                        if (!this.lastHoveredMMI) { return; }
                        const extent = d3.select(this.lastHoveredMMI).data()[0].getStepExtent();
                        // const m = this.scaleX(mmiExtentMargin);
                        const m = Math.max(1, Math.floor(mmiExtentMarginPercent*(extent[1] - extent[0])));
                        // const m = 1;
                        this.updatePlotX([extent[0]-m, extent[1]+m]);
                    }.bind(this))
                    .on("mouseover", function(event) {
                        this.mmiExtentRect
                            .style("opacity", 0.7)
                            .style("outline", "1px rgba(255,255,255,0.5) solid");
                    }.bind(this))
                    .on("mouseleave", function(event) {
                        this.mmiExtentRect
                            .style("opacity", 0.4)
                            .style("outline", null);
                    }.bind(this));
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
                // Change last hovered
                this.lastHoveredMMI = mmi.target;
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
            clearMMIs() {
                debug("clearMMIs");
                this.svg.selectAll(".mmi-marker").remove();
                this.selectedMMI = undefined;
                if (this.mmiExtentRect) {
                    this.mmiExtentRect
                        .attr("x", 0)
                        .attr("width", 0);
                }
                this.createdMMIs.length = 0;
            }
            addAllMMIs(allData, onclick, condense=true) {
                const mediaKeys = new Set();
                for (const simID in allData) {
                    allData[simID].getMediaKeys().forEach(mediaKeys.add, mediaKeys);
                }
                const createdMMIs = this.createdMMIs;
                // Sort all the media datapoints globally
                // This prevents the step ranges of each
                // MMI from overlapping. I.e. if we insert
                // all MMIs in order, that prevents new data
                // from being put in an MMI that is ahead of that data.
                const sortedDatapoints = [];
                for (const key of mediaKeys) {
                    for (const simID in allData) {
                        const data = allData[simID].getData(key);
                        for (const datum of data) {
                            sortedDatapoints.push({
                                key: key,
                                id: simID,
                                datum: datum
                            });
                        }
                    }
                }
                sortedDatapoints.sort((a, b) => a.datum.step - b.datum.step);
                for (const o of sortedDatapoints) {
                    this.addMMI(o.datum, o.id, o.key, allData, onclick, condense, createdMMIs);
                }
                // for (const key of mediaKeys) {
                //     this.addMMIs(key, allData, onclick, condense, createdMMIs);
                // }
            }
            addMMIs(key, allData, onclick, condense=true, createdMMIs=[]) {
                for (const simID in allData) {
                    const data = allData[simID].getData(key);
                    if (data === undefined) { continue; }
                    for (const point of data) {
                        this.addMMI(
                            point,
                            simID,
                            key,
                            allData,
                            onclick,
                            condense,
                            createdMMIs
                        );
                    }
                }
                return createdMMIs;
            }
            addMMI(datum, simID, key, allData, onclick, condense=true, createdMMIs=[]) {
                const width = plotWidth;
                const height = plotHeight;
                const xScale = this.scaleX;
                if (!datum) { return; }
                // Check if this point would be too close to an existing
                // MMI. If so, then get that MMI's MMIData and add this
                // point's data to it.
                const closestMMIIdx = d3.bisectCenter(createdMMIs.map(d => d.step), datum.step);
                // Check the difference in step value and convert to actual length.
                // Compare against the width of MMI markers
                if (closestMMIIdx >= 0 && closestMMIIdx < createdMMIs.length) {
                    debug("step difference: " + Math.abs(createdMMIs[closestMMIIdx].step - datum.step) + ". scale difference: " + Math.abs(xScale(createdMMIs[closestMMIIdx].step) - xScale(datum.step)));
                }
                if (
                    condense &&
                    closestMMIIdx >= 0 &&
                    closestMMIIdx < createdMMIs.length &&
                    Math.abs(xScale(createdMMIs[closestMMIIdx].step) - xScale(datum.step)) < (mmiSideLength+mmiGap)
                ) {
                    // Update existing MMI with new information
                    createdMMIs[closestMMIIdx].selection.data()[0].addData(allData[simID], key, datum.step);
                }
                else {
                    // Create new MMI with new information
                    const markerPoints = getMMIPoints([xScale(datum.step), height-margin.bottom]);
                    const mmiData = new MMIData();
                    mmiData.addData(allData[simID], key, datum.step);
                    this.onClickMMI = onclick;
                    const mmi = createMMI(this.svg, markerPoints)
                        .data([mmiData])
                        .on("mouseover", this.mouseoverMMI.bind(this))
                        .on("mousemove", this.mousemoveMMI.bind(this))
                        .on("mouseleave", this.mouseleaveMMI.bind(this))
                        .on("click", this.clickMMI.bind(this));
                    const created = {step: datum.step, selection: mmi};
                    const insertIdx = sortedIndex(createdMMIs, created, (x) => x.step);
                    createdMMIs.splice(insertIdx, 0, created);
                }
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

            var clip = svg.append("defs").append("svg:clipPath")
                .attr("id", "clip")
                .append("svg:rect")
                .attr("width", width-margin.left-margin.right )
                .attr("height", height-margin.top-margin.bottom )
                .attr("x", margin.left)
                .attr("y", margin.bottom);

            const xScale = d3
                .scaleLinear()
                .domain(extentX)
                // .range([margin.left, width - margin.right - margin.left]);
                .range([margin.left, width - margin.right]);
                // .range([0, width - margin.right]);
            const yScale = d3
                .scaleLinear()
                .domain(extentY)
                .nice()
                // .range([height - margin.bottom - margin.top, margin.top]);
                .range([height - margin.bottom, margin.top]);
                // .range([height - margin.bottom, 0]);

            const xAxis = svg
                .append("g")
                .attr("transform", `translate(0,${height - margin.bottom})`)
                .call(d3.axisBottom(xScale));
            const yAxis = svg
                .append("g")
                .attr("transform", `translate(${margin.left}, 0)`)
                .call(d3.axisLeft(yScale));

            const lines = [];
            for (const simID in allData) {
                const data = allData[simID].getScalar(key);
                lines.push(svg
                    .append("path")
                    .datum(data)
                    .attr("clip-path", "url(#clip)")
                    .attr("fill", "none")
                    .attr("stroke", "steelblue")
                    .attr("stroke-width", 1.5)
                    .attr("d", d3.line()
                        .x(d => xScale(d.step))
                        .y(d => yScale(d.value))
                    ));
            }
            return new Plot(
                svg,
                allData,
                key,
                extentX, 
                extentY,
                xScale,
                yScale,
                xAxis,
                yAxis,
                lines
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
                .attr("class", "mmi-marker")
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