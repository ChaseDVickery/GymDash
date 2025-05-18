import { dataUtils } from "./data.js";

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

        let _setup_done = false;

        class MMIData {
            static COLOR_DEFAULT    = "rgba(0,255,0,0.2)";
            static COLOR_HOVER      = "rgba(0,255,0,1)";
            static COLOR_SELECT     = "rgba(255,50,0,1)";

            constructor() {
                if (!_setup_done) {
                    console.error("Do not use vizUtils until you call setupStaticFields();");
                }
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
                if (!_setup_done) {
                    console.error("Do not use vizUtils until you call setupStaticFields();");
                }
                this.svg = svg;
                this.spots = [];
                this.padding = 5;
                this.width = 54;
                this.height = 20;
                this.tooltipDistance = 10;
                this.spotHeight = 12;
                
                this.node = svg.append("g")
                    .attr("pointer-events", "none")
                    .attr("display", "none")
                    .attr("font-family", "sans-serif")
                    .attr("font-size", "0.5em")
                    .attr("text-anchor", "middle")
                    .attr("dominant-baseline", "text-bottom");
                this.pointer = this.node.append("circle")
                    .attr("r", "2.5")
                    .attr("fill", "orange");
                this.rect = this.node.append("rect")
                    .attr("fill", "white");
                this.#setWidth(this.width);
                // this.#setHeight(this.height);
                // Add 2 spots
                this.spot(0);
                this.spot(1);
            }
            #setWidth(newWidth) {
                if (newWidth < 0) { return; }
                this.width = Math.abs(newWidth);
                // Resize and recenter
                this.rect
                    .attr("x", -(this.width/2))
                    .attr("width", this.width);
            }
            #setHeight(newHeight) {
                if (newHeight < 0) { return; }
                this.height = Math.abs(newHeight);
                // Resize and recenter
                this.rect
                    .attr("y", -(this.height + this.tooltipDistance))
                    .attr("height", this.height);
            }
            show(spotsText) {
                // Fill in spots text
                this.toNumSpots(spotsText.length);
                let maxTextWidth = 0;
                for (let i = 0; i < spotsText.length; i++) {
                    const spot = this.spot(i);
                    if (spot) { spot.text(spotsText[i]); }
                    const spotWidth = spot.node().getBBox().width;
                    maxTextWidth = Math.max(maxTextWidth, spotWidth);
                }
                this.#setWidth((2*this.padding) + maxTextWidth);
                this.node.attr("display", null);
            }
            clearSpots() { for(const s of this.spots) { s.text(""); }}
            spot(idx) {
                if (idx < 0) { return undefined; }
                // Create spots until we reach the desired index.
                while(idx >= this.spots.length) {
                    this.#addSpot();
                }
                return this.spots[idx];
            }
            #addSpot() {
                const newSpot = this.node.append("text");
                // Set spot position
                newSpot
                    .attr("y", -(this.tooltipDistance + this.padding + (this.spotHeight*(this.spots.length + 0.25))));
                this.spots.push(newSpot);
                // Set height to be padding + total height for spots
                this.#setHeight((2*this.padding) + (this.spotHeight*this.spots.length));
                this.pointer.raise();
            }
            #popSpot() {
                const popped = this.spots.pop();
                popped.remove();
                // Set height to be padding + total height for spots
                this.#setHeight((2*this.padding) + (this.spotHeight*this.spots.length));
                return popped;
            }
            toNumSpots(numSpots) {
                if (numSpots < 0) { numSpots = this.spots.length - numSpots; }
                if (numSpots < 0) { numSpots = 0; }
                // Increase spots until we match numSpots
                while (numSpots > this.spots.length) {
                    this.#addSpot();
                }
                // Decrease spots until we match numSpots
                while (numSpots < this.spots.length) {
                    this.#popSpot();
                }
            }
            moveTo(newPoint) {
                this.node.attr("transform", `translate(${newPoint[0]},${newPoint[1]})`);
            }
            hide() {
                this.node.attr("display", "none");
            }
        }

        class Line {
            constructor(selection, ...tags) {
                if (!_setup_done) {
                    console.error("Do not use vizUtils until you call setupStaticFields();");
                }
                this.selection  = selection;
                this.tags       = new Set(tags);
            }
            static none() {
                return new Line(null);
            }
            isValid() {
                return this.selection !== null;
            }
            isHidden() {
                return this.selection.attr("visibility") === "hidden";
            }
            data() {
                return this.selection.datum();
            }
            matches(otherTag) {
                return this.tags.has(otherTag);
            }
        }

        class PlotSettings {
            // Have to do this because I cannot invoke d3 in the class definition.
            // Static fields declared after
            static defaultColorBackground;
            static defaultColorTitle;
            static defaultColorAxis;
            static defaultColorAxisText;
            static defaultColorScale;
            static defaultColorStep;
            

            constructor() {
                if (!_setup_done) {
                    console.error("Do not use vizUtils until you call setupStaticFields();");
                }
                // Colors
                this.bgColor        = PlotSettings.defaultColorBackground;
                this.titleColor     = PlotSettings.defaultColorTitle;
                this.axisColor      = PlotSettings.defaultColorAxis;
                this.axisTextColor  = PlotSettings.defaultColorAxisText;
                this.colorScale     = PlotSettings.defaultColorScale;
                this.colorScaleStep = PlotSettings.defaultColorStep;
            }

            colorAt(idx) {
                // Need to check if a categorical scale or function
                if (Array.isArray(this.colorScale)) {
                    if (Array.isArray(this.colorScale[0])) {
                        const colorArray = this.colorScale[this.colorScale.length-1];
                        return colorArray[idx % colorArray.length];
                    } else {
                        return this.colorScale[idx % this.colorScale.length];
                    }
                } else {
                    const mult = idx * this.colorScaleStep;
                    const colorValue = mult - Math.floor(mult);
                    return this.colorScale(colorValue);
                }                    
            }

            /**
             * Applies the PlotSettings to the given SimPlot.
             * Refreshes the SimPlot when necessary.
             * 
             * @param {SimPlot} plot 
             */
            applyToPlot(plot) {
                plot.bg
                    .attr("fill", this.bgColor);
                this.applyAxisSettings(plot.axisX);
                this.applyAxisSettings(plot.axisY);
                // Reapply the current color scales to all lines
                for (const line of plot.lineSelections()) {
                    const simID = line.attr("data-sim-id");
                    if (!simID) { continue; }
                    line
                        .attr("stroke", plot.colorFor(simID));
                }
            }

            applyAxisSettings(axisSelection) {
                // Axis text color
                axisSelection
                    .style("stroke", this.axisTextColor);
                // Axis line color
                axisSelection.select(".domain")
                    .style("stroke", this.axisColor);
                // Axis tick color
                axisSelection.selectAll(".tick line")
                    .style("stroke", this.axisColor);
            }

            /**
             * Alter the PlotSettings using a given key-value pair
             * and return the same PlotSettings object.
             * 
             * @param {String} settingName 
             * @param {Any} settingValue 
             * @returns 
             */
            changeSetting(settingName, settingValue) {
                if (Object.hasOwn(this, settingName)) {
                    this[settingName]   = settingValue;
                }
                else if (settingName === "axis") {
                    this.axisColor      = settingValue;
                    this.axisTextColor  = settingValue;
                }
                else if (settingName === "main") {
                    this.titleColor     = settingValue;
                    this.axisColor      = settingValue;
                    this.axisTextColor  = settingValue;
                }
                else if (settingName === "secondary") {
                    this.bgColor        = settingValue;
                }
                return this;
            }
        }

        class SimPlot {

            constructor(svg, data, key, scaleX, scaleY, axisX, axisY, lines, simulation_map=null) {
                if (!_setup_done) {
                    console.error("Do not use vizUtils until you call setupStaticFields();");
                }
                this.svg        = svg;
                this.data       = data;
                this.key        = key;
                this.scaleX     = scaleX;
                this.scaleY     = scaleY;
                this.axisX      = axisX;
                this.axisY      = axisY;
                this.lines      = lines;
                this.simulations= simulation_map;
                this.bg         = this.svg.select(".plot-bg");

                this.extentValues= {};
                this.extentSteps= {};

                // Refresh
                this.lastRefreshExtentX = [undefined, undefined];
                this.lastRefreshExtentY = [undefined, undefined];
                
                // Smoothed lines
                this.lastSmoothSpread = 0;
                this.lastSmoothFactor = 1;
                this.lastSmoothExtentX = [undefined, undefined];
                this.lastSmoothExtentY = [undefined, undefined];
                this.smoothed   = {};

                this.tooltip = new Tooltip(this.svg);

                this._mmiCondense = true;
                this._mmisEnabled = false;
                this.onClickMMI = undefined;
                this.selectedMMI = undefined;
                this.lastHoveredMMI = undefined;
                this.hoveredLine = undefined;
                this.createdMMIs = [];

                // Default settings
                this.rescaleY = true;
                this.settings = new PlotSettings();

                this.init();

                this.useSettings(this.settings);
            }

            /**
             * Caches and applies a PlotSettings to this plot.
             * 
             * @param {PlotSettings} settings 
             */
            useSettings(settings) {
                if (settings && settings instanceof PlotSettings) {
                    this.settings = settings;
                    this.settings.applyToPlot(this);
                }
            }

            refreshMMIs() {
                this.clearMMIs();
                this.addAllMMIsFromSims(this.onClickMMI, this._mmiCondense);
            }
            setCondenseMMIs(newValue) {
                this._mmiCondense = newValue;
                if (this._mmisEnabled) {
                    this.refreshMMIs();
                }
            }
            enableMMIs() {
                this._mmisEnabled = true;
                this.refreshMMIs();
            }
            disableMMIs() {
                this._mmisEnabled = false;
                this.clearMMIs();
            }

            numLines() {
                return Object.keys(this.lines).length;
            }
            numSmoothed() {
                return Object.keys(this.smoothed).length;
            }
            lineSelections() {
                return Object.values(this.lines).filter(l => l.isValid()).map(l => l.selection);
            }
            smoothedSelections() {
                return Object.values(this.smoothed).filter(l => l.isValid()).map(l => l.selection);
            }
            /** Return dictionary mapping simID to all associated Lines */
            allLines() {
                const lines = {};
                for (const simID in this.lines) {
                    lines[simID] = [];
                    if (this.lines[simID]) {
                        lines[simID].push(this.lines[simID]);
                    }
                    if (this.smoothed[simID]) {
                        lines[simID].push(this.smoothed[simID]);
                    }
                }
                return lines;
            }
            linesFrom(simID) {
                return this.allLines()[simID];
                // return [...Object.values(this.lines), ...Object.values(this.smoothed)].filter((line) => line.selection.attr("data-sim-id")===simID);
            }
            linesMatching(tag) {
                return [...Object.values(this.lines), ...Object.values(this.smoothed)].filter((line) => line.matches(tag));
            }

            modifyToSelectedSims() {
                // Get the selected simulations
                const lines = this.allLines();
                const selections = this.simulations.selections();
                for (const [simID, simSelection] of Object.entries(selections)) {
                    // Toggle lines on/off
                    for (const line of lines[simID]) {
                        if (!line.isValid()) { continue; }
                        line.selection.attr("visibility", simSelection.checked() ? "visible" : "hidden");
                    }
                    // Alter MMIs
                }
                // Alter the scales and axes so that they are only based on the
                // currently selected simulations
                const asdfasdf =this.extentOfExtents(
                    Object.values(this.simulations.selected())
                        .filter((simSel) => simSel.checked())
                        .map((simSel) => this.extentSteps[simSel.id])
                );
                this.scaleX.domain(this.extentOfExtents(
                    Object.values(this.simulations.selected())
                        .filter((simSel) => simSel.checked())
                        .map((simSel) => this.extentSteps[simSel.id])
                ));
                this.scaleY.domain(this.extentOfExtents(
                    Object.values(this.simulations.selected())
                        .filter((simSel) => simSel.checked())
                        .map((simSel) => this.extentValues[simSel.id])
                ));
                this.axisX.call(d3.axisBottom(this.scaleX));
                this.axisY.call(d3.axisLeft(this.scaleY));
                this.#refreshLines();
                this.refreshMMIs();
            }

            colorFor(simID) {
                const allData = this.simulations.data();
                // Use the iteration order of allData to pick the index
                let idx = 0;
                for (const id in allData) {
                    if (simID === id) {
                        break;
                    }
                    idx += 1;
                }
                return this.settings.colorAt(idx);
            }

            static createLinePlot(simulation_map, key) {
                const svg = getPlotOrMakeNew(undefined);
                const defaultSettings = new PlotSettings();
    
                const allData = simulation_map.data();
    
                const extentY = extentOfKey(allData, key, undefined, "value");
                const extentX = d3.extent([...extentOfKey(allData, key, undefined, "step"), 0]);
    
                const width = plotWidth;
                const height = plotHeight;

                const bg = svg.append("rect")
                    .classed("plot-bg", true)
                    .attr("width", "100%")
                    .attr("height", "100%")
                    .attr("fill", "rgb(230,230,230)");
    
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
    
                const lines = {};
                const extentSteps = {};
                const extentValues = {};
                let idx = 0;
                for (const simID in allData) {
                    const data = allData[simID].getScalar(key);
                    if (!data || data.length < 1) {
                        lines[simID] = Line.none();
                        extentSteps[simID] = [undefined, undefined];
                        extentValues[simID] = [undefined, undefined];
                    } else {
                        extentSteps[simID] = d3.extent(data.map(d => d.step));
                        extentValues[simID] = d3.extent(data.map(d => d.value));
                        const newLineSelection = svg
                            .append("path")
                            .datum(data)
                            .classed("plot-line", true)
                            .attr("data-sim-id", simID)
                            .attr("clip-path", "url(#clip)")
                            .attr("fill", "none")
                            .attr("stroke", defaultSettings.colorAt(idx))
                            .attr("stroke-width", 1.5)
                            .attr("d", d3.line()
                                .x(d => xScale(d.step))
                                .y(d => yScale(d.value))
                            );
                        const newLine = new Line(newLineSelection);
                        lines[simID] = newLine;
                    }
                    idx += 1;
                }
                const plot = new SimPlot(
                    svg,
                    allData,
                    key,
                    xScale,
                    yScale,
                    xAxis,
                    yAxis,
                    lines,
                    simulation_map
                );
                plot.extentSteps = extentSteps;
                plot.extentValues = extentValues;
                plot.modifyToSelectedSims();
                return plot;
            }

            #svgSize() {
                const box = this.svg.node().getBoundingClientRect();
                return {width: box.width, height: box.height};
            }

            removeSim(simID) {
                // Destroy associated lines.
                const lines = this.linesFrom(simID);
                if (!lines) { return; }
                for (const line of lines) {
                    if (line.isValid()) {
                        line.selection.remove();
                    }
                }
                // Remove associated info.
                delete this.lines[simID];
                delete this.extentValues[simID];
                delete this.extentSteps[simID];
                delete this.smoothed[simID];
            }

            /**
             * Resets the data for each existing line and potentially
             * calls smoothing on all lines. Does NOT change the number
             * of lines even if underlying simulation data has changed.
             */
            #refreshLines() {
                const sx = this.scaleX;
                const sy = this.scaleY;
                const eX = sx.domain();
                const eY = sy.domain();
                const sameExtentX = this.lastRefreshExtentX[0] === eX[0] &&
                                    this.lastRefreshExtentX[1] === eX[1];
                const sameExtentY = this.lastRefreshExtentY[0] === eY[0] &&
                                    this.lastRefreshExtentY[1] === eY[1];
                const reloadData = 
                !(
                    sameExtentX &&
                    sameExtentY &&
                    Number.isNaN(eX[0]) &&
                    Number.isNaN(eX[1]) &&
                    Number.isNaN(eY[0]) &&
                    Number.isNaN(eY[1])
                );
                this.lastRefreshExtentX = [eX[0] ? eX[0] : this.lastRefreshExtentX[0], eX[1] ? eX[1] : this.lastRefreshExtentX[1]];
                this.lastRefreshExtentY = [eY[0] ? eY[0] : this.lastRefreshExtentY[0], eY[1] ? eY[1] : this.lastRefreshExtentY[1]];

                // If the lines would be visually different, then
                // update all the orig lines before updating the
                // smoothed ones.
                if (reloadData) {
                    for (const line of this.lineSelections()) {
                        line
                            .style("opacity", 1)
                            .attr("d", d3.line()
                                .x(function(d) { return sx(d.step) })
                                .y(function(d) { return sy(d.value) })
                            );
                    }
                }

                this.smoothLines(this.lastSmoothSpread, this.lastSmoothFactor);
            }
            /**
             * Rebuilds lines by destroying current lines and using the
             * Simulation map to recreate them using the underlying data.
             */
            #rebuildLines() {
                
            }

            addOnLeave(leaveFunc) {
                this.svg.node().addEventListener("customSimPlotOnLeave", leaveFunc);
            }
            addOnEnter(enterFunc) {
                this.svg.node().addEventListener("customSimPlotOnEnter", enterFunc);
            }
            addOnHoverLine(hoverFunc) {
                this.svg.node().addEventListener("customSimPlotOnHover", hoverFunc);
            }
            addOnUnhoverLine(leaveFunc) {
                this.svg.node().addEventListener("customSimPlotOnUnhover", leaveFunc);
            }

            #onhover(event) {
                const width = plotWidth;
                const height = plotHeight;
                
                if (this.numLines() < 1) { return; }
                // We have to scale the absolute pointer offset values by
                // the size of the svg because it can change in size.
                const offsetX = event.offsetX * (width/this.#svgSize().width);
                const offsetY = event.offsetY * (height/this.#svgSize().height);
                // Figure out which line has closest value to mouse position
                const estStep = this.scaleX.invert(offsetX);
                let finalLine;
                let dataPoint;
                let nearestDistance = Infinity;
                const neighborhood = 0;
                // Look for the nearest point on any lines.
                const usedLines = this.numSmoothed() > 0 ? this.smoothedSelections() : this.lineSelections();
                for (const line of usedLines) {
                    if (line.attr("visibility") === "hidden") { continue; }
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
                if (dataPoint && finalLine) {
                    const simID = finalLine.attr("data-sim-id");
                    const sim = this.simulations.get(simID);
                    const simName = sim ? sim.name : "";
                    const step = dataPoint.step;
                    const value = dataPoint.value;
                    this.tooltip.show([
                        `val : ${value.toFixed(2)}`,
                        `step: ${step}`,
                        simName,
                    ]);
                    this.tooltip.moveTo([this.scaleX(dataPoint.step), this.scaleY(dataPoint.value)]);
                }
                // Fire custom events on the simID
                if (dataPoint && finalLine) {
                    // If prior hoveredLine and not the same as new hovered line, 
                    // then trigger unhover event on old line
                    if (this.hoveredLine && this.hoveredLine !== finalLine) {
                        const lastHoveredID = this.hoveredLine.attr("data-sim-id");
                        const customUnhoverEvent = new CustomEvent("customSimPlotOnUnhover", {detail: {simID: lastHoveredID, line: this.hoveredLine}});
                        this.svg.node().dispatchEvent(customUnhoverEvent);
                    }
                    const simID = finalLine.attr("data-sim-id");
                    const sim = this.simulations.get(simID);
                    const customHoverEvent = new CustomEvent("customSimPlotOnHover", {detail: {simID: simID, line: finalLine}});
                    this.svg.node().dispatchEvent(customHoverEvent);
                }
                this.#hoverLine(finalLine);
            }
            #onenter(event) {
                const customEvent = new CustomEvent("customSimPlotOnEnter", {detail: {plot: this, key: this.key}});
                this.svg.node().dispatchEvent(customEvent);
            }
            #onleave(event) {
                this.tooltip.hide();
                this.#hoverLine(undefined);
                const customEvent = new CustomEvent("customSimPlotOnLeave", {detail: {plot: this, key: this.key}});
                this.svg.node().dispatchEvent(customEvent);
            }
            #hoverLine(line) {
                if (this.hoveredLine) {
                    this.hoveredLine
                        .classed("hovered-line", false);
                }
                this.hoveredLine = line;
                if (this.hoveredLine) {
                    this.hoveredLine
                        .classed("hovered-line", true);
                }
                this.#reorderElements();
            }

            init() {
                console.log("INIT");
                // https://developer.mozilla.org/en-US/docs/Web/API/Element#mouse_events
                this.svg
                    .on("mousemove", this.#onhover.bind(this));
                this.svg
                    .on("mouseenter", this.#onenter.bind(this));
                this.svg
                    .on("mouseleave", this.#onleave.bind(this));

                // Double click reset
                this.svg.on("dblclick", this.refresh.bind(this));

                // MMI highlight rectangle
                this.#addMMIRect();

                this.#reorderElements();

                // this.svg.append(this.tooltip.node);
            }

            setSetting_RescaleY(newRescaleY) {
                this.rescaleY = newRescaleY;
            }

            #reorderElements() {
                if (this.hoveredLine) {
                    this.hoveredLine.raise();
                }
                if (this.mmiExtentRect) {
                    this.mmiExtentRect.raise();
                }
                if (this.tooltip) {
                    this.tooltip.node.raise();
                }
            }

            #tryInitBrushes() {
                const width = plotWidth;
                const height = plotHeight;
                // Brushing
                if (!this.brushX) {
                    this.brushX = d3.brushX()
                        .extent([[margin.left, margin.bottom], [width, height-margin.bottom]]);
                    this.svg.append("g").attr("class", "brush").call(
                        this.brushX
                    );
                }
                this.#reorderElements();
            }

            /**
             * Refreshes the Plot display using the updated
             * data value. Usually, the data Object will be
             * altered externally from some other activity,
             * and refresh() will update the Plot to match.
             */
            refresh() {
                // Rebuild the axes
                this.resetX();
                this.resetY();
                // Rebuild the lines
                this.#refreshLines();

                this.refreshMMIs();
            }

            extentX() {
                return this.extentOfExtents(Object.values(this.extentSteps));
            }
            extentY() {
                return this.extentOfExtents(Object.values(this.extentValues));
            }
            extentOfExtents(extentsArray) {
                return d3.extent(
                    extentsArray
                        .filter(e => e && e[0] && e[1])
                        .reduce((all, curr_extent) => all.concat(curr_extent), [])
                );
            }

            clearBrush() {
                this.svg.select(".brush").call(
                    this.brushX.move, null
                );
            }
            /**
             * Clears the svg of all lines and markers as well as clearing
             * certain fields
             */
            clear() {
                this.lines = {};
                this.smoothed = {};
                this.extentValues = {};
                this.extentSteps = {};
                this.svg.selectAll(".plot-line").remove();
                this.svg.selectAll(".mmi-marker").remove();
                selectedMMI = undefined;
                lastHoveredMMI = undefined;
                hoveredLine = undefined;
                createdMMIs = [];
            }

            addBrushX(onbrush, eventType="end") {
                this.#tryInitBrushes();
                this.brushX = this.brushX.on(eventType, onbrush);
            }
            updatePlotEvent(event, otherPlot) {
                if (!event) { return; }
                const extent = event.selection;
                const scaleX = otherPlot.scaleX;
                if (!extent) { return; }
                const startStep = scaleX.invert(extent[0]);
                const endStep = scaleX.invert(extent[1]);
                this.updatePlot([startStep, endStep], this.rescaleY);
            }
            updatePlot(extentX, rescaleY=true) {
                // Update scales and rebuild markers and such
                this.updatePlotX(extentX, false);
                // Optionally scale Y axis based on region's extent
                if (rescaleY) {
                    const startStep = extentX[0];
                    const endStep   = extentX[1];
                    let extentY = [];
                    // Calculate the Y extent in that same region
                    for (const line of this.lineSelections()) {
                        // Retrieve range of data based on step extent
                        const data = line.datum();
                        const steps = data.map(d => d.step);
                        const startIdx = d3.bisect(steps, startStep);
                        const endIdx = d3.bisect(steps, endStep);
                        const dataSlice = data.slice(startIdx, endIdx);
                        // Calculate the new y-extent across all lines
                        const tempExtent = d3.extent(dataSlice.map(d => d.value));
                        extentY = d3.extent([...extentY, ...tempExtent]);
                    }
                    this.updatePlotY(extentY, false);
                } else {
                    this.resetY();
                }
                this.#refreshLines();
                this.refreshMMIs();
            }
            resetX() {
                const extentX = d3.extent([...extentOfKey(this.data, this.key, undefined, "step"), 0]);
                this.scaleX
                    .domain(extentX);
                this.axisX
                    .call(d3.axisBottom(this.scaleX));
                
            }
            resetY() {
                const extentY = extentOfKey(this.data, this.key, undefined, "value");
                this.scaleY
                    .domain(extentY);
                this.axisY
                    .call(d3.axisLeft(this.scaleY));
            }
            updatePlotX(extentX, rebuild=true) {
                this.scaleX.domain(extentX);
                this.axisX.call(d3.axisBottom(this.scaleX));
                if (rebuild) {
                    this.#refreshLines();
                    this.refreshMMIs();
                }
            }
            updatePlotY(extentY, rebuild=true) {
                this.scaleY.domain(extentY);
                this.axisY.call(d3.axisLeft(this.scaleY));
                if (rebuild) {
                    this.#refreshLines();
                    this.refreshMMIs();
                }
            }

            smoothLines(smoothingSpread, smoothingFactor=1) {
                const eX = this.scaleX.domain();
                const eY = this.scaleY.domain();
                const sameSmoothSpread = this.lastSmoothSpread === smoothingSpread;
                const sameSmoothFactor = this.lastSmoothFactor === smoothingFactor;
                const sameExtentX = this.lastSmoothExtentX[0] === eX[0] &&
                                    this.lastSmoothExtentX[1] === eX[1];
                const sameExtentY = this.lastSmoothExtentY[0] === eY[0] &&
                                    this.lastSmoothExtentY[1] === eY[1];
                const reloadData = !(sameSmoothSpread && sameSmoothFactor && sameExtentX && sameExtentY);
                this.lastSmoothSpread = smoothingSpread;
                this.lastSmoothFactor = smoothingFactor;
                this.lastSmoothExtentX = eX;
                this.lastSmoothExtentY = eY;
                // Add them back if we are doing any smoothing
                if (smoothingSpread > 0) {
                    for (const line of this.lineSelections()) {
                        const simID = line.attr("data-sim-id");
                        if (Object.hasOwn(this.smoothed, simID)) {
                            // Trying to reuse exsiting line selections
                            if (!this.smoothed[simID].isValid()) { continue; }
                            this.smoothed[simID].selection
                                .style("opacity", 1)
                                .attr("stroke", line.attr("stroke"))
                                .attr("visibility", line.attr("visibility"))
                            if (reloadData) {
                                // Recalculate smoothed point positions
                                // Get data from orig line
                                const data = line.datum();
                                // Get smoothed version of data
                                const smoothedData = dataUtils.smoothData(data.map(d => d.value), smoothingSpread, smoothingFactor);
                                const finalData = [];
                                for (let i = 0; i < smoothedData.length; i++) {
                                    finalData.push({...(data[i])});
                                    finalData[i].value = smoothedData[i];
                                }
                                this.smoothed[simID].selection
                                .datum(finalData)
                                .attr("d", d3.line()
                                    .x(d => this.scaleX(d.step))
                                    .y(d => this.scaleY(d.value))
                                );
                            }
                            
                                
                        } else {
                            // Get data from orig line
                            const data = line.datum();
                            // Get smoothed version of data
                            const smoothedData = dataUtils.smoothData(data.map(d => d.value), smoothingSpread, smoothingFactor);
                            const finalData = [];
                            for (let i = 0; i < smoothedData.length; i++) {
                                finalData.push({...(data[i])});
                                finalData[i].value = smoothedData[i];
                            }
                            // Append newly smoothed line
                            const newLineSelection = this.svg
                                .append("path")
                                .datum(finalData)
                                .classed("line-smooth", true)
                                .classed("plot-line", true)
                                .attr("data-sim-id", line.attr("data-sim-id"))
                                .attr("clip-path", "url(#clip)")
                                .attr("fill", "none")
                                .style("opacity", 1)
                                .attr("stroke", line.attr("stroke"))
                                .attr("visibility", line.attr("visibility"))
                                .attr("stroke-width", 1.5)
                                .attr("d", d3.line()
                                    .x(d => this.scaleX(d.step))
                                    .y(d => this.scaleY(d.value))
                                )
                            const newLine = new Line(newLineSelection, "smooth");
                            this.smoothed[line.attr("data-sim-id")] = newLine;
                        }
                        
                        // Lower opacity of orig line.
                        line
                            .style("opacity", 0.3);
                    }
                } else {
                    for (const line of this.smoothedSelections()) {
                        // Return orig line opacity
                        line
                            .style("opacity", 0);
                    }
                    for (const line of this.lineSelections()) {
                        // Return orig line opacity
                        line
                            .style("opacity", 1);
                    }
                }
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
                    .style("opacity", 0.4)
                    .on("click", function(event) {
                        console.log("click mmi rect");
                        if (!this.lastHoveredMMI) { return; }
                        const extent = d3.select(this.lastHoveredMMI).data()[0].getStepExtent();
                        const m = Math.max(1, Math.floor(mmiExtentMarginPercent*(extent[1] - extent[0])));
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
            addAllMMIsFromSims(onclick, condense=true) {
                const allData = this.simulations.data();
                const subData = {};
                for (const simID in this.simulations.selected()) {
                    // Check if the simulation's DataReport has a scalar
                    // key relating to this plot. Include it if so.
                    if (allData[simID].isScalar(this.key)) {
                        subData[simID] = allData[simID];
                    }
                }
                this.addAllMMIs(subData, onclick, condense);
            }
            addAllMMIs(allData, onclick, condense=true) {
                this.onClickMMI = onclick;
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
            }
            addMMI(datum, simID, key, allData, onclick, condense=true, createdMMIs=[]) {
                const width = plotWidth;
                const height = plotHeight;
                const xScale = this.scaleX;
                if (!this._mmisEnabled) { return; }
                if (!datum) { return; }
                // Check if this point would be too close to an existing
                // MMI. If so, then get that MMI's MMIData and add this
                // point's data to it.
                const closestMMIIdx = d3.bisectCenter(createdMMIs.map(d => d.step), datum.step);
                // Check the difference in step value and convert to actual length.
                // Compare against the width of MMI markers
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
                    // this.onClickMMI = onclick;
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
         * @param {Object<dataUtils.DataReport>} allData 
         * @param {String} key 
         * @param {Array<String>} simIDs 
         * @param {value_or_step} dataPointAttribute 
         * @returns 
         */
        const extentOfKey = function(allData, key, simIDs, dataPointAttribute="value") {
            // Use all simulations if IDs is not specified
            if (simIDs === undefined) {
                simIDs = Object.keys(allData);
            }
            const extent = [Infinity, -Infinity];
            if (simIDs.length < 1) {
                return extent;
            }
            for (const simID of simIDs) {
                // If the given key is not scalar and we are trying to find the
                // extent of it's "value", then that's not possible. We can find
                // the extent of its "step" or "wall_time", but "value" only
                // makes sense for scalars.
                if (!allData[simID].isScalar(key) && dataPointAttribute === "value") {
                    continue;
                }
                if (!allData[simID].has(key)) { continue; }
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
                .attr("stroke-opacity", 0.2)
                .attr("fill", mmiDefaultColor);
        }

        /**
         * Taken from:
         * https://stackoverflow.com/questions/35969656/how-can-i-generate-the-opposite-color-according-to-current-color
         * for invertColorHex
         */
        function padZero(str, len) {
            len = len || 2;
            var zeros = new Array(len).join('0');
            return (zeros + str).slice(-len);
        }
        /**
         * Inverts a color represented with a hex code, optionally
         * converting to black or white depending on which has
         * more contrast to the input color. This was taken and modified
         * from: https://stackoverflow.com/questions/35969656/how-can-i-generate-the-opposite-color-according-to-current-color
         * 
         * @param {String} hex 
         * @param {Boolean} bw 
         * @returns {Color}
         */
        const invertColorHex = function(hex, bw) {
            if (hex.indexOf('#') === 0) {
                hex = hex.slice(1);
            }
            // convert 3-digit hex to 6-digits.
            if (hex.length === 3) {
                hex = hex[0] + hex[0] + hex[1] + hex[1] + hex[2] + hex[2];
            }
            if (hex.length !== 6) {
                throw new Error('Invalid HEX color.');
            }
            var r = parseInt(hex.slice(0, 2), 16),
                g = parseInt(hex.slice(2, 4), 16),
                b = parseInt(hex.slice(4, 6), 16);
            const inverted = invertColorValues(r,g,b,bw);
            // pad each with zeros and return
            return "#" + padZero(inverted.r.toString(16)) + padZero(inverted.g.toString(16)) + padZero(inverted.b.toString(16));
        }
        /**
         * Inverts a color represented with a rgb code, optionally
         * converting to black or white depending on which has
         * more contrast to the input color. RGB color should look like:
         * rgb(#,#,#) or #,#,#. Values should be in the range of 0-255.
         * 
         * @param {String} rgb 
         * @param {Boolean} bw 
         * @returns {Color}
         */
        const invertColorRGB = function(rgb, bw) {
            let compact = true;
            if (rgb.toLowerCase().indexOf("rgb(") === 0) {
                compact = false;
                rgb = rgb.slice(4);
            }
            if (rgb.endsWith(")")) {
                rgb = rgb.slice(0, rgb.length-1);
            }
            const components = rgb.split(",");
            if (components.length != 3) { throw new Error("Invalid RGB color."); }
            var r = parseInt(components[0], 10),
                g = parseInt(components[1], 10),
                b = parseInt(components[2], 10);
            const inverted = invertColorValues(r,g,b,bw);
            // pad each with zeros and return
            const internal = inverted.r.toString(10) + "," + inverted.g.toString(10) + "," + inverted.b.toString(10);
            if (compact) {
                return internal;
            }
            return "rgb(" + internal + ")";
        }
        /**
         * Inverts a color string.
         * 
         * @param {String} colorString 
         * @param {Boolean} bw 
         */
        const invertColor = function(colorString, bw) {
            colorString.startsWith
            if (colorString.startsWith("rgb")) {
                return invertColorRGB(colorString, bw);
            }
            if (colorString.startsWith("#")) {
                return invertColorHex(colorString, bw);
            }
            throw new Error("Could not find way to invert color string.");
        }
        const invertColorValues = function(r,g,b, bw) {
            if (bw) {
                // https://stackoverflow.com/a/3943023/112731
                return (r * 0.299 + g * 0.587 + b * 0.114) > 186
                    ? {r: 0, g: 0, b: 0}
                    : {r: 255, g: 255, b: 255};
            }
            // invert color components
            r = (255 - r);
            g = (255 - g);
            b = (255 - b);
            return {r: r, g: g, b: b};
        }

        const setupStaticFields = function() {
            PlotSettings.defaultColorBackground = "rgb(230,230,230)";
            PlotSettings.defaultColorTitle      = "rgb(25,25,25)";
            PlotSettings.defaultColorAxis       = "rgb(25,25,25)";
            PlotSettings.defaultColorAxisText   = "rgb(25,25,25)";
            PlotSettings.defaultColorScale      = d3.scaleSequential(d3.interpolateSinebow);
            PlotSettings.defaultColorStep       = 0.27;
            _setup_done = true;
        }

        return {
            SimPlot,
            PlotSettings,
            setupStaticFields,
            invertColorRGB,
            invertColorHex,
            invertColor
        };
    }
)();

export { vizUtils };