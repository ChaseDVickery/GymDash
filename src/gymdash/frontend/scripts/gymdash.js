import { resourceUsageUtils, resourceUsageDisplayUtils } from "./utils/usage.js";
import { dataUtils } from "./utils/data.js";
import { vizUtils } from "./utils/viz.js";
import { mediaUtils } from "./utils/media_utils.js";
import { apiURL } from "./utils/api_link.js";
// console.log(range);

const tryBtn        = document.querySelector("#try-api-btn");
const tryBtnOut     = document.querySelector("#try-api-out");
const testBtn       = document.querySelector("#test-api-btn");
const testBtnOut    = document.querySelector("#test-api-out");
const resourceBtn       = document.querySelector("#resource-usage-btn");
const resourceBtnOut    = document.querySelector("#resource-usage-out");
const scalarDataTestBtn       = document.querySelector("#scalar-test-btn");
const scalarDataTestBtnOut    = document.querySelector("#scalar-test-out");
const imageTestOut    = document.querySelector("#test-image");
const imageTestBtn    = document.querySelector("#image-test-btn");
const startSimTestBtn    = document.querySelector("#start-test-sim-btn");
const simTestTimestepsSlider = document.querySelector("#test-sim-steps-slider")
const queryProgressTestBtn = document.querySelector("#query-test-btn");
const stopSimTestBtn = document.querySelector("#stop-test-btn");
const fillHistoryTestBtn = document.querySelector("#fill-sim-history-test-btn");
const deleteAllSimsTestBtn = document.querySelector("#delete-all-sims-test-btn");
const deleteSelectedSimsTestBtn = document.querySelector("#delete-selected-sims-test-btn");



// Constants
const defaultMaxSimStatusUpdatePeriod = 5000;   // (ms)
const defaultSimProgressUpdateInterval = 5000;  // (ms)
const defaultTimeout = 2.5; // (s)
const noID = "00000000-0000-0000-0000-000000000000"; // (str(UUID))

// Structures
// sim_selections store information
// let sim_selections = {};
// let allData = {};
// let allRecentStatus = {};
const mainPlots = [];
const allPlots = [];
// let hoveredSimSelection;
let canQuerySimStatus = true;

// By the end, sim_selections, allData, and allRecentStatus should not be used.
// Also hoveredSimSelection?


// Sidebar
const simSidebar = document.querySelector(".sim-selection-sidebar");
const deselectAllBtn            = simSidebar.querySelector("#deselect-all-btn");
const selectAllBtn              = simSidebar.querySelector("#select-all-btn");
// Control
const startPanel                = document.querySelector("#start-panel");
const controlColumn             = document.querySelector(".control-column");
const controlPanel              = document.querySelector("#control-panel");
const controlResponsePanel      = document.querySelector("#control-response-panel");
const controlRequestDetails     = document.querySelector("#control-request-details-panel");
const queryColumn               = document.querySelector(".query-column");
const queryPanel                = document.querySelector("#query-panel");
const queryResponsePanel        = document.querySelector("#query-response-panel");
const configNameEntry           = startPanel.querySelector("#config-name1");
const configKeyEntry            = startPanel.querySelector("#config-key1");
const configFamilyEntry         = startPanel.querySelector("#config-family1");
const configTypeEntry           = startPanel.querySelector("#config-type1");
const startSimBtn               = startPanel.querySelector("#start-sim-btn");
const queueSimBtn               = startPanel.querySelector("#queue-sim-btn");
const sendControlBtn            = document.querySelector("#send-control-btn");
const sendQueryBtn              = document.querySelector("#send-query-btn");

// Settings
const settingBarTitle           = document.querySelector("#setting-bar-title");
const settingBarContent         = document.querySelector("#setting-bar-content");
const plotSmoothSlider_Setting  = document.querySelector("#plot-smoothing-slider");
const plotSmoothLabel_Setting   = document.querySelector("label[for=plot-smoothing-slider]");
const rescaleDetailsY_Setting   = document.querySelector("#rescale-details-axis");

let plotSmoothValue             = 0;
let rescaleDetailsAxisY         = false;

// General
const tooltip                   = document.querySelector(".tooltip")
// Plots
const plotArea                  = document.querySelector("#plots-area");
// Multimedia Filter
const mmInstancePanel           = document.querySelector(".media-panel");
const mmFilterSortPanel         = mmInstancePanel.querySelector("#media-filter-sort-panel");
const mmFilterSortOptionsArea   = mmFilterSortPanel.querySelector(".filter-sort-options-area");
const mmFilterSortHeader        = mmFilterSortPanel.querySelector(".filter-sort-label");
const mmFilterCheckKey          = mmFilterSortPanel.querySelector("#mm-filter-key");
const mmFilterCheckSim          = mmFilterSortPanel.querySelector("#mm-filter-sim");
const mmFilterCheckStep         = mmFilterSortPanel.querySelector("#mm-filter-step");
const mmFilterAreaKey           = mmFilterSortPanel.querySelector("#mm-filter-key-area");
const mmFilterAreaSim           = mmFilterSortPanel.querySelector("#mm-filter-sim-area");
const mmFilterAreaStep          = mmFilterSortPanel.querySelector("#mm-filter-step-area");
// Multimedia Displays
const mmImageSubmediaArea       = mmInstancePanel.querySelector("#image-panel > .media-instance-area");
const mmAudioSubmediaArea       = mmInstancePanel.querySelector("#audio-panel > .media-instance-area");
const mmVideoSubmediaArea       = mmInstancePanel.querySelector("#video-panel > .media-instance-area");
const mmImageHeader             = mmInstancePanel.querySelector("#image-panel > .media-type-label");
const mmAudioHeader             = mmInstancePanel.querySelector("#audio-panel > .media-type-label");
const mmVideoHeader             = mmInstancePanel.querySelector("#video-panel > .media-type-label");

// Prefabs
const prefabSimSelectBox        = document.querySelector(".prefab.sim-selection-box");
const prefabKwargPanel          = document.querySelector(".prefab.kwarg-panel");
const prefabKwarg               = document.querySelector(".prefab.kwarg");
const prefabImageMedia          = document.querySelector(".prefab.multimedia-instance-panel.image-instance-panel");
const prefabAudioMedia          = document.querySelector(".prefab.multimedia-instance-panel.audio-instance-panel");
const prefabVideoMedia          = document.querySelector(".prefab.multimedia-instance-panel.video-instance-panel");
const prefabResizerBar          = document.querySelector(".prefab.resizer-bar");
const prefabcontrolRequestBox   = document.querySelector(".prefab.control-request");
const prefabFilterDiscrete      = document.querySelector(".prefab.discrete-filter-setting");
const prefabFilterBetween       = document.querySelector(".prefab.between-filter-setting");
prefabSimSelectBox.remove();
prefabKwargPanel.remove();
prefabKwarg.remove();
prefabImageMedia.remove();
prefabAudioMedia.remove();
prefabVideoMedia.remove();
prefabResizerBar.remove();
prefabcontrolRequestBox.remove();
prefabFilterDiscrete.remove();
prefabFilterBetween.remove();

class SimSelection {
    constructor(element, config, simID, startChecked=false) {
        // Elements
        this.id = simID;
        this.element = element;
        this.label = element.querySelector("label");
        this.input = element.querySelector(".sim-selection-checkbox");
        this.cancelButton = element.querySelector(".cancel-sim-button");
        this.meter = element.querySelector(".radial-meter");
        this.outer = this.meter.querySelector(".outer")

        // Setup
        this.element.classList.remove("prefab");

        // Set up new selection box
        this.selectionID = `${simID}`;
        this.input.id            = this.selectionID;
        this.input.checked       = startChecked;
        this.label.htmlFor       = this.selectionID;
        this.label.textContent   = config.name;
    }

    checked() { return this.input.checked; }
    isDone() { return this.meter.classList.contains("complete"); }    
    removeElement() { if (this.element) { this.element.remove(); } }

    completeProgress(failOrSuccess=null) {
        this.meter.classList.add("complete");
        this.meter.classList.remove("incomplete");
        if (failOrSuccess === "fail" || failOrSuccess === "success") {
            this.meter.classList.add(failOrSuccess);
        }
    }
    updateProgress() {
        const meter = this.meter;
        const is_done = this.isDone();
        if (is_done) { return Promise.resolve(); }
        const outer = this.outer;
        return queryProgress(this.id, is_done)
            .then((info) => {
                if (!info) { return Promise.resolve(info); }
                if (!validID(info.id)) { return Promise.resolve(info); }
                debug(info);
                if (info.is_done) {
                    if (info.cancelled || info.failed) {
                        this.completeProgress("fail");
                    } else {
                        this.completeProgress("success");
                    }
                }
                if (Object.hasOwn(info, "progress")) {
                    if (info.progress[1] === 0) { return info; }
                    outer.style.setProperty("--prog-num", `${info.progress[0]}`);
                    outer.style.setProperty("--prog-den", `${info.progress[1]}`);
                    outer.style.setProperty("--prog", `${100*info.progress[0]/info.progress[1]}%`);
                    if (simulations.isSimHovered(this.id)) {
                        tooltipUpdateToSimSelection(this.id);
                    }
                }
            })
            .catch((error) => {
                console.error(`Update sim selection progress error: ${error}`)
            });
    }
}

class Simulation {
    constructor(simID) {
        // id: The simID
        // active: whether it is active
        // selection: the associated SimSelection
        // data: DataReport holding all the data
        // status: SimStatus object
        // meta: meta information associated with sim
        this.id         = simID;
        this.active     = false;
        this.selection  = null;
        this.data       = new dataUtils.DataReport(simID);
        this.status     = null;
        this.meta       = null;
    }

    checked() {
        return  this.selection && 
                this.selection.checked();
    }

    deleteSelection() {
        if (!this.selection) { return; }
        this.selection.removeElement();
    }

    /**
     * @param {SimSelection} newSelection
     */
    setSelection(newSelection) {
        this.selection = newSelection;
    }
    /**
     * @param {Boolean} newActive 
     */
    setActive(newActive) {
        this.active = newActive;
    }
    setStatus(newStatus) {
        this.status = newStatus;
        if (simulations.isSimHovered(this.id)) {
            tooltipUpdateToSimSelection(this.id);
        }
    }
    /**
     * Creates and returns a new Simulation with the
     * given SimSelection.
     * 
     * @param {String} simID
     * @param {SimSelection} newSelection 
     * @returns Simulation
     */
    static fromSelection(simID, newSelection) {
        const newSimulation = new Simulation(simID);
        newSimulation.setSelection(newSelection);
        return newSimulation;
    }
}

class SimulationMap {
    constructor() {
        this.simulations = {}
        this.hoveredSimSelection;
    }

    isSimHovered(simID) {
        return  Object.hasOwn(this.simulations, simID) &&
                this.hoveredSimSelection &&
                this.hoveredSimSelection === this.simulations[simID].selection;
    }

    /**
     * Invokes a callback function for each simulation
     * stored in the map. Callback arguments are:
     *  simID: ID of the simulation
     *  simulation: The sim itself
     * 
     * @param {Function} callbackFn 
     */
    forEach(callbackFn) {
        for (const simID in this.simulations) {
            callbackFn(simID, this.simulations[simID]);
        }
    }

    /**
     * Returns object mapping from simID to SimSelection
     * for ALL tracked Simulations.
     * @returns {Object}
     */
    selections() {
        const mapping = {};
        for (const simID in this.simulations) {
            mapping[simID] = this.simulations[simID].selection;
        }
        return mapping;
    }
    /**
     * Returns object mapping from simID to SimSelection
     * for ALL tracked Simulations whose SimSelections are checked.
     * @returns Object
     */
    selected() {
        const mapping = {};
        for (const simID in this.simulations) {
            if (this.simulations[simID].checked()) {
                mapping[simID] = this.simulations[simID].selection;
            }
        }
        return mapping;
    }

    /**
     * Returns the simulation at simID.
     * 
     * @param {String} simID 
     * @returns {Simulation}
     */
    get(simID) {
        return this.simulations[simID];
    }

    /**
     * Adds a simulation to the map. If a simulation with the same
     * ID already exists, replace it.
     * 
     * @param {Simulation} simulation 
     */
    add(simulation) {
        this.simulations[simulation.id] = simulation;
    }
    /**
     * Removes a property from the simulations Object corresponding
     * to the simulation ID. In other words, it removes a Simulation
     * from the map.
     * 
     * @param {String} simID 
     */
    remove(simID) {
        delete this.simulations[simID];
    }
    clear() {
        this.simulations = {};
    }

    combineData(dataReport) {
        const simID = dataReport.simID;
        const simulation = this.get(simID);
        if (!simulation) {
            console.error("Trying to combine data report for ${simID} but this simulation does not exist in SimulationMap.");
            return;
        }
        simulation.data.addDataReport(dataReport);
    }

    /**
     * Deletes and recreates all the SimSelections for all known
     * Simulations. Retrieves simulation history from backend to
     * create new Simulations if they don't exist in the map yet.
     */
    refreshSimulations() {
        // First gather all those that are selected/checked
        const tempSelected = this.selected();
        // Delete all SimSelections
        this.forEach((_, sim) => sim.deleteSelection() )
        // Retrieve all simulation history data from backend
        fetch(apiURL("get-sims-history"))
        .then((response) => response.json())
        .then((infos) => {
            // Should be list of StartedSimulationInfo
            debug(infos);
            // Iterate StartedSimulationInfos, create new selection for each
            infos.forEach(info => {
                const simID = info.sim_id;
                const config = info.config;
                if (!validID(simID)) {
                    return info;
                }
                // Create new Simulation if it doesn't exist yet
                if (!Object.hasOwn(this.simulations, simID)) {
                    this.simulations[simID] = new Simulation(simID);
                }
                const simulation = this.simulations[simID];
                // Create new SimSelection and add to corresponding Simulation
                const startChecked = Object.hasOwn(tempSelected, simID);
                const newSelection = createSimSelection(config, simID, startChecked);
                simulation.setSelection(newSelection);
                // Note: Check to see whether to set the Simulation to active or not.
                if (info.is_done) {
                    simulation.setActive(true);
                    if (info.cancelled || info.failed) {
                        newSelection.completeProgress("fail");
                    } else {
                        newSelection.completeProgress("success");
                    }
                } else {
                    simulation.setActive(true);
                }
                debug(info);
            });
            return infos;
        })
        .catch((error) => {
            console.error("Error: " + error);
        });
    }
}

// https://stackoverflow.com/questions/44447847/enums-in-javascript-with-es6
const FilterType = Object.freeze({
    NONE:       Symbol("none"),
    DISCRETE:   Symbol("discrete"),
    MULTIDISCRETE: Symbol("multidiscrete"),
    BETWEEN:    Symbol("between"),
    MULTIBETWEEN: Symbol("multibetween"),
});

class Filter {
    constructor(element) {
        this.element = element;
        this.filterType = FilterType.NONE;

        this.inputs = [];
        
        if (element.classList.contains("discrete-filter-setting")) {
            this.filterType = FilterType.DISCRETE;
            this.inputs.push(this.element.querySelector("input"));
        } else if (element.classList.contains("between-filter-setting")) {
            this.filterType = FilterType.BETWEEN;
            this.inputs.push(this.element.querySelector(".between-filter-begin"));
            this.inputs.push(this.element.querySelector(".between-filter-end"));
        } else if (element.classList.contains("discrete-filter-area")) {
            this.filterType = FilterType.MULTIDISCRETE;
            const allOptions = this.element.querySelectorAll(".discrete-filter-setting");
            for (const option of allOptions) {
                this.inputs.push(option.querySelector("input"));
            }
        } else if (element.classList.contains("between-filter-area")) {
            this.filterType = FilterType.MULTIBETWEEN;
            const allOptions = this.element.querySelectorAll(".between-filter-setting");
            for (const option of allOptions) {
                this.inputs.push(option.querySelector(".between-filter-begin"));
                this.inputs.push(option.querySelector(".between-filter-end"));
            }
        }
        else {
            console.error("Filter is of unknown type");
        }
    }

    getInputs() {
        return [...this.inputs];
    }

    /**
     * Applies the filter to an Array of data objects.
     * When accessFunction is supplied, it is used to access a specific
     * key of each data element for filtering. Returns the
     * filtered data array or the original array if not filtered.
     * 
     * @param {Array} data 
     * @param {Function} accessFunction
     * @returns Filtered data.
     */
    apply(data, accessFunction=(x) => x) {
        if (this.filterType === FilterType.NONE) { return data; }
        if (this.filterType === FilterType.DISCRETE) {
            // If this filter input is not checked, then we don't need to filter.
            if (!this.inputs[0].checked) { return data; }
            // Get the desired filter value from the element
            const filterValue = this.element.dataset.filterValue;
            return data.filter((datum) => accessFunction(datum) === filterValue);
        }
        else if (this.filterType === FilterType.BETWEEN) {
            const startValue = this.inputs[0].value;
            const endValue = this.inputs[1].value;
            return data.filter((datum) => {
                const finalValue = accessFunction(datum);
                return finalValue >= startValue && finalValue <= endValue
            });
        }
        // Works like discrete, but ANY of the options may match and the
        // value will be included. If we were to just chain discrete filters,
        // it would work like an AND filter (all must be true), but
        // multidiscrete works like an OR filter (any must be true).
        else if (this.filterType === FilterType.MULTIDISCRETE) {
            const filterValues = this.inputs
                .filter((i) => i.checked)
                .map((q) => q.parentElement.dataset.filterValue);
            debug("filterValues");
            debug(filterValues);
            return data.filter((datum) => {
                const finalValue = accessFunction(datum);
                debug("finalValue");
                debug(finalValue);
                return filterValues.some((filterValue) => filterValue === finalValue);
            });
        }
        // Similar to multidiscrete, filters using an OR rule using the
        // between-type filtering. I.e. "if the data value is within this
        // range or that range, then we include it".
        else if (this.filterType === FilterType.MULTIBETWEEN) {
            const startValues = [];
            const endValues = [];
            for (let i = 0; i < this.inputs.length; i+=2) {
                startValues.push(this.inputs[i].value);
                endValues.push(this.inputs[i+1].value);
            }
            return data.filter((datum) => {
                const finalValue = accessFunction(datum);
                for (let i = 0; i < startValues.length; i++) {
                    if (finalValue >= startValues[i] && finalValue <= endValues[i]) {
                        debug(`Value ${finalValue} is >= than ${startValues[i]} and <= ${endValues[i]}`);
                        return true;
                    }
                }
                return false;
            });
        }

        console.error("Could not properly apply any filter for some reason.");
        return data;
    }
}


// Variables
const simulations = new SimulationMap();
let selectedControlRequest;
let selectedMMIData;

const testImageOutputs = []

let testSimTimesteps = Number(simTestTimestepsSlider.value)

function call_random() {
    return fetch(apiURL("random"));
    // return fetch(apiURL("big-data1000");
    // return fetch(apiURL("big-data100000");
    // return fetch(apiURL("big-data1000000");
}

function getSimName(simIDorSelection) {
    if (typeof simIDorSelection === "string") {
        const selections = getAllSelections();
        if (Object.hasOwn(getAllSelections(), simIDorSelection)) {
            return selections[simIDorSelection].querySelector("label").textContent;
        }
    } else {
        return simIDorSelection.querySelector("label").textContent;
    }
}
/**
 * Return a mapping from all simulation selection IDs to the simulation
 * selection nodes.
 * 
 * @returns Object mapping each simulation ID to the selection object
 */
function getAllSelections() {
    const mapping = Array.from(document.querySelectorAll(".sim-selection-checkbox")).reduce(
        (curr_map, curr_chkbox) => {
            curr_map[curr_chkbox.id] = curr_chkbox.parentElement.parentElement;
            return curr_map;
        },
        {}
    )
    return mapping;
}
/**
 * Return a mapping from each selected simulation ID to the selected
 * selection object.
 * 
 * @returns Object mapping each selected simulation ID to the selection object.
 */
function getSelectedSelections() {
    const mapping = Array.from(document.querySelectorAll(".sim-selection-checkbox")).reduce(
        (curr_map, curr_chkbox) => {
            if (curr_chkbox.checked) {
                curr_map[curr_chkbox.id] = curr_chkbox.parentElement.parentElement;
            }
            return curr_map;
        },
        {}
    )
    return mapping;
}
function getSelectionFor(simID) {
    return getAllSelections()[simID];
}
function getSelectedData() {
    // const selectedSelections = getSelectedSelections();
    const selectedSelections = simulations.selected();
    const selectedData = {};
    for (const id in selectedSelections) {
        selectedData[id] = simulations.get(id).data;
    }
    return selectedData;
}
function forEachSelection(doThis) {
    const selections = getAllSelections();
    for (const simID in selections) {
        doThis(selections[simID]);
    }
}
function selectAll() {
    forEachSelection((selection) => {
        const input = selection.querySelector(".sim-selection-checkbox")
        input.checked = true;
    })
}
function deselectAll() {
    forEachSelection((selection) => {
        const input = selection.querySelector(".sim-selection-checkbox")
        input.checked = false;
    })
}

function displayNumberOutput(num) {
    tryBtnOut.textContent = num;
}
function displayTestNumberOutput(outputs) {
    testBtnOut.textContent = outputs;
}

function getNumber() {
    return call_random()
        .then((response) => {
            if (!response.ok) {
                throw new Error("Network response was not ok");
            }
            // .json() returns a Promise with the result being the JSON info
            return response.json();
        })
        .then((response) => {
            displayNumberOutput(response.value);
            return response;
        })
}

function timeGetNumber() {
    let start = Date.now();
    return call_random()
        .then((response) => {
            if (!response.ok) {
                throw new Error("Network response was not ok");
            }
            let time = Date.now() - start;
            return Promise.resolve({time});
        });
}

function testNumberAPI() {
    const numRequests = 1000;
    // Make n simultaneous API calls and time
    const times = [];
    const promises = [];
    for (let i = 0; i < numRequests; i++) {
        promises.push(
            timeGetNumber().then((response) => {
                times.push(response.time);
                return response;
            }).then((response) => {
                displayTestNumberOutput(times);
            })
        );
    }
    Promise.all(promises).then((responses) => {
        // Process all the response times.
        const max = Math.max(...times);
        const min = Math.min(...times);
        const avg = times.reduce((sum, value) => {return sum + value;}) / times.length;
        const metricString = `You requested ${numRequests} numbers. We measured ${times.length} times. Metrics (min, avg, max): (${min/1000}, ${avg/1000}, ${max/1000})s`;
        console.log(metricString);
        setTimeout(displayTestNumberOutput(metricString), 0);
    });
}

function displayResourceUsage() {
    resourceUsageUtils.getResourceUsageDetailed()
    // resourceUsageUtils.getResourceUsageSimple()
        .then((usageValues) => {
            let usageString = "";
            for (const [key, value] of Object.entries(usageValues)) {
                usageString += `\t${key} = ${value}`;
            }
            usageString += `\tcpu=${(usageValues.cpus_percent.reduce((sum, value) => { return sum + value})/usageValues.cpus_percent.length).toFixed(2)}%`;
            usageString += `\tmemory=${((usageValues.memory_total - usageValues.memory_available)*100 / usageValues.memory_total).toFixed(2)}%`;
            usageString += `\tdisk=${((usageValues.disk_total - usageValues.disk_available)*100 / usageValues.disk_total).toFixed(2)}%`;
            resourceBtnOut.textContent = usageString;
        });
}

function displayScalarDataTest() {
    dataUtils.getAllNewScalars()
        .then((results) => {
            scalarDataTestBtnOut.textContent = `Recent logged results: ${results}`;
            console.log(results);
        });
}

function setImageOutput(index, imgSrc) {
    while (index >= testImageOutputs.length) {
        const img = document.createElement("img");
        document.body.appendChild(img);
        testImageOutputs.push(img);
    }
    testImageOutputs[index].src = imgSrc;
}
function displayVideoTest() {
    updateData()
        .then((allDataReports) => {
            createPlots();
        });
}


function updateData() {
    const dataRetrievalPromises = [];
    const allDataReports = [];
    const selectionOptions = simulations.selected();
    for (const simID in selectionOptions){
        debug(`Getting new data for sim: ${simID}`);
        dataRetrievalPromises.push(
            dataUtils.getAll(simID, [], [], true)
            // dataUtils.getRecent(simID, [], [], true)
                .then((dataReport) => {
                    debug("Got data report.");
                    debug(dataReport);
                    allDataReports.push(dataReport);
                    return Promise.resolve(dataReport);
                })
                .catch((error) => {
                    console.error("Problem updating data for simulation " + simID + ". Returning promise of empty data report");
                    return Promise.resolve(new dataUtils.DataReport(simID));
                })
        );
    }
    return Promise.all(dataRetrievalPromises)
        .then((allDataReports) => {
            // Add the data from each new report to the current
            // Simulation DataReports
            for (let j = 0; j < allDataReports.length; j++) {
                simulations.combineData(allDataReports[j]);
                // const simID = allDataReports[j].simID;
                // if (!Object.hasOwn(allData, simID)) {
                //     allData[simID] = new dataUtils.DataReport(simID);
                // }
                // allData[simID].addDataReport(allDataReports[j]);
            }
            debug("ALL DATA");
            return Promise.resolve(allDataReports);
        })
        .catch((error) => {
            console.error(`Error processing all data reports: ${error}`)
        });
}

function startSimTest() {
    const data = {
        name: "cartpole",
        sim_key: "my_custom_sim",
        // sim_key: "stable_baselines/ppo",
        sim_family: "",
        sim_type: "",
        kwargs: {
            "num_steps": testSimTimesteps,
            "episode_trigger": 50,
            "policy": "MlpPolicy",
            "env": "LunarLander-v3",
            "algorithm": "ppo"
        }
    };
    fetch(apiURL("start-new-test"), {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify(data),
    })
    .then((response) => {
        const info = response.json();
        console.log(info);
        return info;
    })
    .catch((error) => {
        console.error("Error: " + error);
    });
}

function stopSimTest() {
    const simulationQuery = {
        id: "dummy_id",
        timeout: 0.0,
        stop_simulation: {
            triggered: true,
            value: "stop, please"
        }
    };
    fetch(apiURL("query-sim"), {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify(simulationQuery),
    })
    .then((response) => {
        const info = response.json();
        console.log(info);
        return info;
    })
    .catch((error) => {
        console.error("Error: " + error);
    })
}

function testQueryProgress() {
    const simulationQuery = {
        id: "dummy_id",
        timeout: 1.0,
        stop_simulation: {}, // This would contain fields 'triggered' and 'value'
        progress: {
            triggered: true,
            value: "give me this information, please",
        } // This would contain fields 'triggered' and 'value'
    };
    fetch(apiURL("query-sim"), {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify(simulationQuery),
    })
    .then((response) => {
        const info = response.json();
        console.log(info);
        return info;
    })
    .catch((error) => {
        console.error("Error: " + error);
    })
}

function createQueryBody(simID, timeout=defaultTimeout) {
    return {
        id: simID,
        timeout: timeout
    };
}
function queryProgress(simID, onlyStatus=False) {
    if (!validID(simID)) { return Promise.resolve({id: noID}); }
    const q = {
        id: simID,
        timeout: defaultTimeout,
        is_done:    { triggered: true, value: null, },
        cancelled:  { triggered: true, value: null, },
        failed:     { triggered: true, value: null, },
    };
    if (!onlyStatus) {
        q.progress = { triggered: true, value: null, };
    }
    return query(q);
}
function controlStopSim(simID) {
    if (!validID(simID)) { return Promise.resolve({id: noID}); }
    const q = {
        id: simID,
        timeout: defaultTimeout,
        stop_simulation: {triggered: true, value: null},
    };
    return fetch(apiURL("cancel-sim"), {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify(q),
    }).then((response) => { return response.json(); });
}
// Returns a promise of the simulation query
function query(queryBody) {
    queryBody.error_details = { triggered: true, value: null };
    console.log(`Sending query: ${queryBody}`);
    console.log(queryBody);
    return fetch(apiURL("query-sim"), {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify(queryBody),
    }).then((response) => { return response.json(); });
}
function querySimulationStatus(simIDs) {
    if (!canQuerySimStatus) {
        const existingStatuses = {};
        for (const simID of simIDs) {
            existingStatuses[simID] = simulations.get(simID).status;
        }
        return Promise.resolve(existingStatuses);
    }
    canQuerySimStatus = false;
    return fetch(apiURL("get-sim-status"), {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({ ids: simIDs }),
    }).then((response) => { return response.json(); });
}


// Utils
function convertKwargValue(valueString) {
    // Return the input if it is not a string
    if (typeof valueString !== "string") { return valueString; }
    // Trim string
    valueString = valueString.trim();
    // Bool check
    if (valueString.toLowerCase() === "true")   { return true; }
    else if (valueString.toLowerCase() === "false")  { return false; }
    // If starts with a quote, then there's really no other
    // type it could be but string
    else if (valueString.startsWith('\"') || valueString.startsWith('\'')) {
        let startIdx = 0;
        let endIdx = valueString.length-1;
        // Find start index beyond quote marks
        while (startIdx < valueString.length) {
            if (valueString.charAt(startIdx) !== "\'" && valueString.charAt(startIdx) !== "\"") {
                break;
            }
            startIdx += 1;
        }
        // Find index right before final sequence of quotes
        while (endIdx >= 0) {
            if (valueString.charAt(endIdx) !== "\'" && valueString.charAt(endIdx) !== "\"") {
                endIdx += 1;
                break;
            }
            endIdx -= 1;
        }
        return valueString.substring(startIdx, endIdx);
    }
    // Try to convert to number
    else if (!Number.isNaN(Number(valueString))) {
        return Number(valueString);
    }
    // Try JSON parsing or Just return the trimmed value
    else {
        try {
            return JSON.parse(valueString);
        } catch (e) {
            return valueString;
        }
    }
}
/**
 * Gathers all keyword arguments from input kwarg panel into a single
 * kwarg object.
 */
function getKwargs(elementWithKwargPanel) {
    const kwargArea = elementWithKwargPanel.querySelector(".kwarg-area");
    const allKwargEntries = kwargArea.querySelectorAll(".kwarg");
    const kwargs = {};
    for (const kwargEntry of allKwargEntries) {
        // Only include if kwarg is a DIRECT DESCENDENT of this kwarg panel
        if (kwargEntry.parentElement !== kwargArea) { continue; }
        // Get key and value for kwarg
        let key = kwargEntry.querySelector(".key").value.trim();
        let val = kwargEntry.querySelector(".value").value.trim();
        let subkwargsPanel = kwargEntry.querySelector(".kwarg-subkwargs").querySelector(".kwarg-panel");
        if (key === "") { continue; }
        if (val === "") { val = true; }
        const splitKey = key.split(/\s+/);
        key = splitKey.join("_");
        // If we have subkwargs, use those instead of value
        if (subkwargsPanel !== null) {
            val = getKwargs(subkwargsPanel);
        } else {
            val = convertKwargValue(val);
        }
        kwargs[key] = val;
    }
    console.log("KWARGS");
    console.log(kwargs);
    return kwargs;
}
function isSimHovered(simSelection) {
    return hoveredSimSelection && hoveredSimSelection === simSelection;
}
function updateAllSimSelectionProgress() {
    // We only want to update progress for simulations that are active.
    // Otherwise, we don't care about showing progress for inactive sims.
    for (const [simID, sim] of Object.entries(simulations.simulations)) {
        if (sim.active) {
            sim.selection.updateProgress();
            // updateSimSelectionProgress(simID, sim.selection);
        }
    }
}
// /**
//  * 
//  * @param {String} simID 
//  * @param {SimSelection} simSelection 
//  * @returns 
//  */
// function updateSimSelectionProgress(simID, simSelection) {
//     if (!simSelection) { return; }
//     const meter = simSelection.meter;
//     // if (meter.classList.contains("complete")) { return; }
//     const is_done = simSelection.isDone();
//     if (is_done) { return Promise.resolve(); }
//     const outer = simSelection.outer;
//     return queryProgress(simID, is_done)
//         .then((info) => {
//             console.log(info);
//             if (info.is_done) {
//                 meter.classList.add("complete");
//                 meter.classList.remove("incomplete");
//                 if (info.cancelled || info.failed) {
//                     meter.classList.add("fail");
//                 } else {
//                     meter.classList.add("success");
//                 }
//             }
//             if (Object.hasOwn(info, "progress")) {
//                 if (info.progress[1] === 0) { return info; }
//                 outer.style.setProperty("--prog-num", `${info.progress[0]}`);
//                 outer.style.setProperty("--prog-den", `${info.progress[1]}`);
//                 outer.style.setProperty("--prog", `${100*info.progress[0]/info.progress[1]}%`);
//                 if (isSimHovered(simSelection)) {
//                     tooltipUpdateToSimSelection(simID);
//                 }
//             }
//         })
//         .catch((error) => {
//             console.error(`Update sim selection progress error: ${error}`)
//         });
// }
function updateAllSimSelectionStatus() {
    const simIDs = Object.keys(simulations.selections());
    return querySimulationStatus(simIDs)
        .then((info) => {
            // Dict: simID -> SimStatus
            for (const simID in info) {
                const statusInfo = info[simID];
                simulations.get(simID).setStatus(statusInfo);
                // allRecentStatus[simID] = statusInfo;
                // // if (isSimHovered(sim_selections[simID])) {
                // if (simulations.isSimHovered(simID)) {
                //     tooltipUpdateToSimSelection(simID);
                // }
            }
        });
}
function updateSimSelectionStatus(simID) {
    return querySimulationStatus([simID])
        .then((info) => {
            // Dict: simID -> SimStatus
            for (const simID in info) {
                const statusInfo = info[simID];
                simulations.get(simID).setStatus(statusInfo);
                // allRecentStatus[simID] = statusInfo;
                // // if (isSimHovered(sim_selections[simID])) {
                // if (simulations.isSimHovered(simID)) {
                //     tooltipUpdateToSimSelection(simID);
                // }
            }
        });
}

function refreshSimulationSidebar() {
    simulations.refreshSimulations();
}

function sendSingleQuery(simID) {
    // Gather kwargs
    const kwargs = getKwargs(controlColumn.querySelector(".kwarg-panel"));
    // Create and send custom query
    const queryBody = createQueryBody(simID);
    queryBody.custom_query = {triggered: true, value: kwargs};
    return query(queryBody);
}
function sendQuery() {
    const selections = getSelectedSelections();
    const promises = [];
    for (const simID in selections) {
        promises.push(sendSingleQuery(simID));
    }
    Promise.all(promises)
        .then((queryInfos) => {
            console.log("QUERY INFOS:");
            console.log(queryInfos);
        })
}

function repositionTooltip(tt, element, direction="right") {
    const rect = element.getBoundingClientRect();
    const ttrect = tt.getBoundingClientRect();
    if (direction === "right") {
        tt.style.left = `${rect.right}px`;
        tt.style.top = `${rect.top + ((rect.height-ttrect.height)/2)}px`;
    }
    else if (direction === "left") {
        tt.style.left = `${rect.left-ttrect.width}px`;
        tt.style.top = `${rect.top + ((rect.height-ttrect.height)/2)}px`;
    }
    else if (direction === "top") {
        tt.style.left = `${rect.left + ((rect.width-ttrect.width)/2)}px`;
        tt.style.top = `${rect.top - ttrect.height}px`;
    }
    else if (direction === "bottom") {
        tt.style.left = `${rect.left + ((rect.width-ttrect.width)/2)}px`;
        tt.style.top = `${rect.bottom}px`;
    }
}

function tooltipUpdateToSimSelection(simID) {
    // const selection = getSelectionFor(simID);
    const selection = simulations.get(simID).selection;
    if (!selection) { return; }
    const meter = selection.meter;
    const status = simulations.get(simID).status;
    if (meter.classList.contains("fail")) {
        let newText = "Failed";
        if (status) {
            newText += `: ${status.details}`;
        }
        tooltip.textContent = newText;
    }
    else if (meter.classList.contains("success")) {
        let newText = "Success";
        if (status) {
            newText += `: ${status.details}`;
        }
        tooltip.textContent = newText;
    }
    else {
        const progressMeter = selection.outer;
        const progNum = progressMeter.style.getPropertyValue("--prog-num");
        const progDen = progressMeter.style.getPropertyValue("--prog-den");
        const progPer = progressMeter.style.getPropertyValue("--prog");
        const progPerValue = Number(progPer.substring(0, progPer.length-1)).toFixed(2);
        tooltip.textContent = `${progNum}/${progDen} (${progPerValue}%)`;
    }
}

// Turns the entry into a SimulationStartConfig data layout
function entryToConfig() {
    const name = configNameEntry.value;
    const key = configKeyEntry.value;
    const family = configFamilyEntry.value;
    const type = configTypeEntry.value;
    const kwargs = getKwargs(startPanel.querySelector(".kwarg-panel"));
    const config = {
        name: name,
        sim_key: key,
        sim_family: family,
        sim_type: type,
        kwargs: kwargs
    };
    return config;
}
function createSimSelection(config, simID, startChecked=true) {
    const newSelectionElement = prefabSimSelectBox.cloneNode(true);
    const newSelection = new SimSelection(newSelectionElement, config, simID, startChecked);
    simSidebar.appendChild(newSelection.element);
    // Set up cancel button
    newSelection.cancelButton.addEventListener(
        "click",
        stopSimulationFromSelection.bind(null, newSelection)
    );
    // Set up tooltip hover
    newSelection.element.addEventListener(
        "mouseover",
        function(e) {
            simulations.hoveredSimSelection = newSelection;
            tooltip.style.visibility = "visible";
            // updateSimSelectionStatus(simID);
            updateAllSimSelectionStatus().then((p) => {
                tooltipUpdateToSimSelection(simID);
                repositionTooltip(tooltip, newSelection.element, "right");
            })
        }
    );
    newSelection.element.addEventListener(
        "mouseout",
        function(e) {
            simulations.hoveredSimSelection = undefined;
            tooltip.style.visibility = null;
            tooltip.textContent = "";
        }
    );
    // Return selection box
    return newSelection;
}
function validID(simID) { return noID !== simID; }
function queueSimulation() {
    // Read relevant information and gather kwargs
    const config = entryToConfig();
    fetch(apiURL("queue-new-sim"), {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify(config),
    })
    .then((response) => response.json())
    .then((info) => {
        console.log(info);
        const simID = info.id;
        if (!validID(simID)) {
            return info;
        }
        const newSelection = createSimSelection(config, simID);
        const simulation = Simulation.fromSelection(simID, newSelection);
        simulation.setActive(true);
        // Store new simulation in tracker
        simulations.add(simulation);
        return info;
    })
    .catch((error) => {
        console.error("Error: " + error);
    });
}
function startSimulation() {
    // Read relevant information and gather kwargs
    const config = entryToConfig();
    fetch(apiURL("start-new-test"), {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify(config),
    })
    .then((response) => response.json())
    .then((info) => {
        console.log(info);
        const simID = info.id;
        if (!validID(simID)) {
            return info;
        }
        const newSelection = createSimSelection(config, simID);
        const simulation = Simulation.fromSelection(simID, newSelection);
        simulation.setActive(true);
        // Store new simulation in tracker
        simulations.add(simulation);
        return info;
    })
    .catch((error) => {
        console.error("Error: " + error);
    });
}
/**
 * 
 * @param {SimSelection} simSelection
 */
function stopSimulationFromSelection(simSelection) {
    if (!simSelection) { return; }
    const input = simSelection.input;
    const meter = simSelection.meter;
    const simID = simSelection.id;
    // Set stopping visuals and remove from sim_selections
    // delete sim_selections[simID];
    console.log(simSelection);
    debug(`Getting simulation with ID: ${simID}`);
    simulations.get(simID).setActive(false);
    meter.classList.add("cancelling");
    stopSimulation(simID)
        .then((response) => {
            console.log(`Done calling stop simulation on ${simID}`);

            simulations.get(simID).selection.updateProgress()
                .then((response) => {
                    // Put back in simSelection and stop cancellation visual
                    simulations.get(simID).setActive(true);
                    meter.classList.remove("cancelling");
                    if (simulations.isSimHovered(simID)) {
                        tooltipUpdateToSimSelection(simID);
                    }
                })
        })
        .catch((error) => {
            console.error(`Error while stopping simulation: ${error}`);
        });
}
// Sends the request to actually stop the given simulation
function stopSimulation(simID) {
    return controlStopSim(simID);
}

function showDeleteAllSimulationsOption() {
    deleteAllSimulations();
}
function deleteAllSimulations() {
    // Visually indicate all running sims as cancelling
    // for (const [key, simSelection] of Object.entries(sim_selections)) {
    for (const [key, simSelection] of Object.entries(simulations.selections())) {
        const meter = simSelection.meter;
        const simID = key;
        // Set stopping visuals and remove from sim_selections
        // delete sim_selections[simID];
        simulations.get(simID).setActive(false);
        meter.classList.add("cancelling");
    }
    fetch(apiURL("delete-all-sims"))
        .then((response) => { return response.json(); })
        .then((info) => {
            // sim_selections = {};
            // allData = {};
            refreshSimulationSidebar();
            simulations.clear();
        })
        .catch((error) => { console.error(`Error while deleting all simulations: ${error}`)});
}
function deleteSelectedSimulations() {
    console.log("deleteSelectedSimulations");
    // Visually indicate all running sims as cancelling
    const simIDs = [];
    // for (const [key, simSelection] of Object.entries(getAllSelections())) {
    for (const [key, simSelection] of Object.entries(simulations.selected())) {
        const meter = simSelection.meter;
        const simID = key;
        simIDs.push(simID);
        // Set stopping visuals and remove from sim_selections
        // delete sim_selections[simID];
        simulations.get(simID).setActive(false);
        meter.classList.add("cancelling");
        console.log("deleting " + simID);
    }
    deleteSimulations(simIDs);
}
function deleteSimulations(simIDs) {
    console.log("SIM IDS");
    console.log(simIDs);
    fetch(apiURL("delete-sims"), {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({ids: simIDs}),
    })
    .then((response) => { return response.json(); })
    .then((info) => {
        // sim_selections = {};
        // allData = {};
        refreshSimulationSidebar();
        for (const simID of simIDs) {
            simulations.remove(simID);
        }
    })
    .catch((error) => { console.error(`Error while deleting all simulations: ${error}`)});
}


function setupKwargBox(kwargPanel) {
    const addKwargBtn = kwargPanel.querySelectorAll(".add-kwarg");
    for (const btn of addKwargBtn) {
        console.log(`Adding event listener to btn ${btn}`);
        btn.addEventListener("click", addKwarg.bind(null, kwargPanel));
    }
}
function setupKwargBoxes() {
    // Get kwarg boxes
    const kwargBoxes = document.querySelectorAll(".kwarg-panel");
    // Add listener to kwarg box add button
    for (const box of kwargBoxes) {
        setupKwargBox(box);
    }
}
function addKwarg(kwargPanel) {
    if (!kwargPanel.classList.contains("kwarg-panel")) {
        console.error(`Not adding kwarg because panel ${kwargPanel} is not a kwarg-panel.`);
        return;
    }
    const kwargArea = kwargPanel.querySelector(".kwarg-area");
    const newKwarg = prefabKwarg.cloneNode(true);
    newKwarg.classList.remove("prefab");
    // Setup listeners on new kwarg
    const removeBtn = newKwarg.querySelector(".remove-kwarg-btn");
    if (removeBtn !== null) {
        removeBtn.addEventListener("click", removeKwarg.bind(null, newKwarg));
    }
    const addSubkwargBtn = newKwarg.querySelector(".add-subkwarg-btn");
    if (addSubkwargBtn !== null) {
        addSubkwargBtn.addEventListener("click", addSubkwargs.bind(null, newKwarg));
    }
    kwargArea.appendChild(newKwarg);
}
function removeKwarg(kwargRow) {
    kwargRow.parentElement.removeChild(kwargRow);
}
function addSubkwargs(kwargRow) {
    const subkwargArea = kwargRow.querySelector(".kwarg-subkwargs");
    const newSubkwargs = prefabKwargPanel.cloneNode(true);
    setupKwargBox(newSubkwargs);
    subkwargArea.appendChild(newSubkwargs);
}
function clearKwargBox(kwargPanel, deleteRows=false) {

}

function selectControlRequest(requestBox, detailsString) {
    if (selectedControlRequest) {
        selectedControlRequest.classList.remove("contrast-box-opp");
        selectedControlRequest.classList.add("contrast-box");
    }
    selectedControlRequest = requestBox;
    if (selectedControlRequest) {
        selectedControlRequest.classList.add("contrast-box-opp");
        selectedControlRequest.classList.remove("contrast-box");
    }
    controlRequestDetails.textContent = detailsString;
}
function setupControlRequest(simID, simSelection, request_data) {
    const requestBox = prefabcontrolRequestBox.cloneNode(true);
    const previewText = `${getSimName(simSelection)}: ${request_data.details}`;
    const detailText =
`sim='${getSimName(simSelection)}'
id=${simID}
details=${request_data.details}
channel_key=${request_data.key}
subkeys=${request_data.subkeys}`;
    // Set the preview text
    requestBox.querySelector(".control-request-preview").textContent = previewText;
    // Ready event listener to show details on click
    requestBox.addEventListener("click", selectControlRequest.bind(null, requestBox, detailText));
    // Set event listener for removal button
    requestBox.querySelector(".control-request-delete").addEventListener("click", (e) => {
        e.stopPropagation();
        if (selectedControlRequest === requestBox) {
            selectControlRequest(undefined, "");
        }
        requestBox.remove();
    });

    controlResponsePanel.appendChild(requestBox);
}
function updateControlRequestQueue(requests_model) {
    const requests = requests_model.requests;
    const selections = getAllSelections();
    for (const simID in requests) {
        const selection = selections[simID];
        for (const channel_key in requests[simID]) {
            console.log(requests[simID]);
            console.log(requests[simID][channel_key]);
            for (const request of requests[simID][channel_key]) {
                setupControlRequest(simID, selection, request);
                // const requestBox = prefabcontrolRequestBox.cloneNode(true);
                // requestBox.textContent = `sim='${getSimName(selection)}'(${simID}), channel='${request.key}', details='${request.details}'.`;
                // controlResponsePanel.appendChild(requestBox);
            }
        }        
    }
}

setupKwargBoxes();


const fullResourcePreview = document.querySelector(".resource-preview.full-preview")
const miniResourcePreview = document.querySelector(".resource-preview.mini-preview")
resourceUsageDisplayUtils.setupResourceUsageDisplay(fullResourcePreview);
resourceUsageDisplayUtils.setupResourceUsageDisplay(miniResourcePreview, true);

tryBtn.addEventListener("click", getNumber);
testBtn.addEventListener("click", testNumberAPI);
resourceBtn.addEventListener("click", displayResourceUsage);
scalarDataTestBtn.addEventListener("click", displayScalarDataTest);
imageTestBtn.addEventListener("click", displayVideoTest);
startSimTestBtn.addEventListener("click", startSimTest);
queryProgressTestBtn.addEventListener("click", testQueryProgress);
stopSimTestBtn.addEventListener("click", stopSimTest);
fillHistoryTestBtn.addEventListener("click", refreshSimulationSidebar);
deleteAllSimsTestBtn.addEventListener("click", showDeleteAllSimulationsOption);
deleteSelectedSimsTestBtn.addEventListener("click", deleteSelectedSimulations);


simTestTimestepsSlider.addEventListener("change", (e) => {
    testSimTimesteps = Number(e.target.value);
});

// Listening for control requests sent from server
const ctrlReqSrc = new EventSource(apiURL("get-control-requests"));
ctrlReqSrc.onopen = () => {
    console.log("EventSource connected");
}
ctrlReqSrc.addEventListener("retrieval", (event) => {
    const requests = JSON.parse(event.data);
    updateControlRequestQueue(requests);
});

deselectAllBtn.addEventListener("click", deselectAll);
selectAllBtn.addEventListener("click", selectAll);
startSimBtn.addEventListener("click", startSimulation);
queueSimBtn.addEventListener("click", queueSimulation);
sendControlBtn.addEventListener("click", sendQuery);
sendQueryBtn.addEventListener("click", sendQuery);

// MMI Filter Objects
mmImageHeader.addEventListener("click", toggleMediaType.bind(null, dataUtils.DataReport.IMAGE));
mmAudioHeader.addEventListener("click", toggleMediaType.bind(null, dataUtils.DataReport.AUDIO));
mmVideoHeader.addEventListener("click", toggleMediaType.bind(null, dataUtils.DataReport.VIDEO));
mmFilterSortHeader.addEventListener("click", toggleDisplay.bind(null, mmFilterSortOptionsArea));
mmFilterCheckKey.addEventListener("change", refreshMMIDisplay);
mmFilterCheckSim.addEventListener("change", refreshMMIDisplay);
mmFilterCheckStep.addEventListener("change",refreshMMIDisplay);
mmFilterCheckKey.addEventListener("change", toggleDisplay.bind(null, mmFilterAreaKey));
mmFilterCheckSim.addEventListener("change", toggleDisplay.bind(null, mmFilterAreaSim));
mmFilterCheckStep.addEventListener("change", toggleDisplay.bind(null, mmFilterAreaStep));
toggleDisplay(mmFilterAreaKey);
toggleDisplay(mmFilterAreaSim);
toggleDisplay(mmFilterAreaStep);

// Settings
plotSmoothSlider_Setting.addEventListener("input", (e) => {
    changeSetting_PlotSmooth(Number(e.target.value));
    plotSmoothValue = Number(e.target.value);
    plotSmoothLabel_Setting.textContent = `Smoothing: (${plotSmoothValue.toFixed(2)})`;
});
rescaleDetailsY_Setting.addEventListener("change", (e) => {
    changeSetting_RescaleDetailsAxisY(rescaleDetailsY_Setting.checked);
})
settingBarTitle.addEventListener("click", toggleDisplay.bind(null, settingBarContent))
toggleDisplay(settingBarContent);

// Setup intervals
// Update progress periodically
setInterval(updateAllSimSelectionProgress, defaultSimProgressUpdateInterval);
// Allow simulation status queries periodically
setInterval(function() { canQuerySimStatus = true; }, defaultMaxSimStatusUpdatePeriod);
// setInterval(updateAllSimSelectionStatus, defaultSimProgressUpdateInterval);


refreshSimulationSidebar();
openTab(null, "tab-analyze");


function changeSetting_PlotSmooth(newSmooth) {
    // Clamp smoothing value
    plotSmoothValue = 0.5 * Math.min(1, Math.max(0, newSmooth));
    // Apply smoothing to all plots
    for (const plot of allPlots) {
        plot.smoothLines(plotSmoothValue);
    }
}
function changeSetting_RescaleDetailsAxisY(shouldRescale) {
    for (const plot of allPlots) {
        plot.setSetting_RescaleY(shouldRescale);
        plot.updatePlot(plot.scaleX.domain(), shouldRescale);
    }
}


function toggleDisplay(element) {
    if (element.style.display === "none") {
        element.style.display = "";
    } else {
        element.style.display = "none";
    }
}
function toggleMediaType(type) {
    if (type === dataUtils.DataReport.IMAGE) {
        toggleDisplay(mmImageSubmediaArea);
    } else if (type === dataUtils.DataReport.AUDIO) {
        toggleDisplay(mmAudioSubmediaArea);
    } else if (type === dataUtils.DataReport.VIDEO) {
        toggleDisplay(mmVideoSubmediaArea);
    }
}

function clearMainPlot() {
    const svgs = plotArea.querySelectorAll("svg");
    for (let i = 0; i < svgs.length; i++) {
        plotArea.removeChild(svgs[i]);
    }
}
function clearMediaPanel() {
    const submediaAreas = document.querySelectorAll(".media-instance-area");
    for (let i = 0; i < submediaAreas.length; i++) {
        const mmInstancePanels = submediaAreas[i].querySelectorAll(".multimedia-instance-panel");
        for (const mmip of mmInstancePanels) {
            submediaAreas[i].removeChild(mmip);
        }
    }
}
function showMMInstance(simID, type, datum) {
    let panel;
    if (type === dataUtils.DataReport.IMAGE) {
        panel = prefabImageMedia.cloneNode(true);
        mmImageSubmediaArea.appendChild(panel);
        const mediaElement = panel.querySelector(".media");
        mediaElement.src = datum.value;
    }
    else if (type === dataUtils.DataReport.AUDIO) {
        panel = prefabAudioMedia.cloneNode(true);
        mmAudioSubmediaArea.appendChild(panel);
        const mediaElement = panel.querySelector(".media");
        mediaElement.src = datum.value;
    }
    else if (type === dataUtils.DataReport.VIDEO) {
        panel = prefabVideoMedia.cloneNode(true);
        mmVideoSubmediaArea.appendChild(panel);
        const mediaElement = panel.querySelector(".media");
        const sourceElement = mediaElement.querySelector("source");
        sourceElement.src = datum.value;
        sourceElement.type = "video/mp4";
    }
    if (!panel) { return panel; }
    
    const caption = panel.querySelector(".media-info");
    const simSelection = getAllSelections()[simID];
    caption.textContent = `sim: ${getSimName(simSelection)}`;
    return panel;
}
// function gatherFilters(filterPanel) {
//     const filters = [];
//     const discreteFilterArea   = filterPanel.querySelectorAll(".discrete-filter-area");
//     const betweenFilters    = filterPanel.querySelectorAll(".between-filter-setting");
//     // Create Filters for each area
//     for (const elem of discreteFilterArea) {
//         filters.push(new Filter(elem));
//     }
//     for (const elem of betweenFilters) {
//         filters.push(new Filter(elem));
//     }
//     return filters;
// }
function filterMMIData(data) {
    debug(`MMI data starts with ${data.length} datapoints`);
    // Gather up filter information from inputs
    const useKey = mmFilterCheckKey.checked;
    const useSim = mmFilterCheckSim.checked;
    const useStp = mmFilterCheckStep.checked;
    if (useKey) {
        const filter = new Filter(mmFilterAreaKey);
        data = filter.apply(data, (datum) => datum.key);
    }
    debug(`Key filtered: ${data.length} datapoints`);
    if (useSim) {
        const filter = new Filter(mmFilterAreaSim);
        data = filter.apply(data, (datum) => datum.simID);
    }
    debug(`Sim filtered: ${data.length} datapoints`);
    if (useStp) {
        const filter = new Filter(mmFilterAreaStep);
        data = filter.apply(data, (datum) => datum.datum.step);
    }
    debug(`Step filtered: ${data.length} datapoints`);
    return data;
    // datum -> datum -> wall_time
    // datum -> datum -> value
    // datum -> datum -> step
    // datum -> simID
    // datum -> key
    // datum -> type
    // Apply all filters based on filter type
}
function displayMMIData(mmiData) {
    console.log("display mmi data");
    console.log(mmiData);
    clearMediaPanel();
    let data = mmiData.getData();
    data = filterMMIData(data);
    console.log("filtered mmi data");
    console.log(data);
    for (const datapoint of data) {
        const newInstancePanel = showMMInstance(datapoint.simID, datapoint.type, datapoint.datum);
    }
}
function updateMMIFilters(mmiData) {
    const data = mmiData.getData();

    // Clear the filter input areas
    mmFilterAreaKey.replaceChildren();
    mmFilterAreaSim.replaceChildren();
    mmFilterAreaStep.replaceChildren();
    // Update the areas with new inputs matching
    // the mmi data

    // Get unique keys
    const keySet = new Set(data.map((d) => d.key));
    // Get unique simIDs
    const idSet = new Set(data.map((d) => d.simID));
    // Get last (greatest) step value
    const lastStep = data.reduce(
        (currGreatest, currDatum) => currDatum.datum.step > currGreatest ? currDatum.datum.step : currGreatest,
        0
    )
    
    const inputs = [];

    // Setup key options
    const prefix = "mmi-filter-option-";
    let k = 0;
    for (const key of keySet) {
        const newOption = prefabFilterDiscrete.cloneNode(true);
        const newCheckbox = newOption.querySelector("input");
        const newLabel = newOption.querySelector("label");
        const newID = `${prefix}${k}`;
        newOption.dataset.filterValue = key;
        newCheckbox.id = newID;
        newCheckbox.name = newID;
        newCheckbox.value = newID;
        newCheckbox.checked = true;
        newLabel.htmlFor = newID;
        newLabel.textContent = key;
        mmFilterAreaKey.appendChild(newOption);
        inputs.push(newCheckbox);
        k += 1;
    }
    // Setup id options
    for (const id of idSet) {
        const newOption = prefabFilterDiscrete.cloneNode(true);
        const newCheckbox = newOption.querySelector("input");
        const newLabel = newOption.querySelector("label");
        const newID = `${prefix}${k}`;
        newOption.dataset.filterValue = id;
        newCheckbox.id = newID;
        newCheckbox.name = newID;
        newCheckbox.value = newID;
        newCheckbox.checked = true;
        newLabel.htmlFor = newID;
        newLabel.textContent = getSimName(id);
        mmFilterAreaSim.appendChild(newOption);
        inputs.push(newCheckbox);
        k += 1;
    }
    // Setup step options
    const newOption = prefabFilterBetween.cloneNode(true);
    const newBegin = newOption.querySelector(".between-filter-begin");
    const newEnd = newOption.querySelector(".between-filter-end");
    const newLabel = newOption.querySelector("label");
    const newID = `${prefix}${k}`;
    // newOption.dataset.filterValue = id;
    newBegin.id = newID + "-begin";
    newBegin.name = newID + "-begin";
    newBegin.value = "0";
    newEnd.id = newID + "-end";
    newEnd.name = newID + "-end";
    newEnd.value = lastStep;
    newLabel.textContent = "Steps";
    mmFilterAreaStep.appendChild(newOption);
    inputs.push(newBegin);
    inputs.push(newEnd);
    k += 1;

    // Add a change listener to retrigger the MMI display
    // when a filter input is changed
    for (const newInput of inputs) {
        newInput.addEventListener("change", (e) => {
            displayMMIData(mmiData);
        });
    }
}
function refreshMMIDisplay() {
    if (selectedMMIData) {
        displayMMIData(selectedMMIData);
    }
}
function onClickMMI(d) {
    const mmiData = d3.select(d.target).data()[0];
    selectedMMIData = mmiData;
    updateMMIFilters(mmiData);
    displayMMIData(mmiData);
}
function createPlots() {
    // const key = "rollout/ep_rew_mean";
    const key = "loss/train";
    // const key = "loss/val";
    // const key = "acc/val";  
    // const key = "my_number";

    mainPlots.splice(0, mainPlots.length);
    allPlots.splice(0, allPlots.length);
    clearMainPlot();

    const condense = true;
    const selectedData = getSelectedData();

    const allScalarKeys = new Set();
    for (const simID in selectedData) {
        const report = selectedData[simID];
        report.scalar_keys.forEach(k => allScalarKeys.add(k));
    }

    if (Object.keys(selectedData).length <= 0) { return; }

    const plot = vizUtils.createLinePlotForKey(key, selectedData);
    const detailsPlot = vizUtils.createLinePlotForKey(key, selectedData);
    mainPlots.push(plot);
    mainPlots.push(detailsPlot);
    allPlots.push(plot);
    allPlots.push(detailsPlot);

    plot.smoothLines(plotSmoothValue);
    detailsPlot.smoothLines(plotSmoothValue);

    plot.addAllMMIs(selectedData, onClickMMI, condense);
    detailsPlot.addAllMMIs(selectedData, onClickMMI, condense);
    plot.addBrushX(function(event) {
        detailsPlot.updatePlotEvent(event, plot);
    }, "brush");
    
    d3.select("#plots-area").append(() => plot.svg.node());
    d3.select("#plots-area").append(() => detailsPlot.svg.node());

    for (const k of allScalarKeys) {
        const p = vizUtils.createLinePlotForKey(k, selectedData);
        allPlots.push(p);
        p.smoothLines(plotSmoothValue);
        d3.select("#plots-area").append(() => p.svg.node());
    }
}


addResizeBar(plotArea, "ew");
addResizeBar(startPanel);
// addResizeBar(controlColumn);
addResizeBar(queryColumn, "ew", "before");
// addResizeBar(queryColumn, "ew", "after");
// queryPanel

// Adapted from:
// https://stackoverflow.com/questions/8960193/how-to-make-html-element-resizable-using-pure-javascript
function addResizeBar(resizablePanel, direction="ew", position="after") {
    var startX, startY, startWidth, startHeight;
    const newBar = prefabResizerBar.cloneNode(true);
    newBar.classList.add(direction);
    if (position === "after") {
        resizablePanel.after(newBar);
    } else if (position === "before") {
        resizablePanel.before(newBar);
    }

    // var resizer = document.querySelector(".resizer-bar");
    // var p = plotArea;
    function initDrag(e) {
        startX = e.clientX;
        startY = e.clientY;
        startWidth = parseInt(document.defaultView.getComputedStyle(resizablePanel).width, 10);
        startHeight = parseInt(document.defaultView.getComputedStyle(resizablePanel).height, 10);
        document.documentElement.addEventListener('mousemove', doDrag, false);
        document.documentElement.addEventListener('mouseup', stopDrag, false);
    }
    
    function doDrag(e) {
        if (direction === "ew") {
            const change = e.clientX;
            if (position === "after") {
                resizablePanel.style.width = (startWidth + change - startX) + 'px';
            } else {
                resizablePanel.style.width = (startWidth + startX - change) + 'px';
            }
            
        } else if (direction === "ns") {
            const change = e.clientY;
            if (position === "after") {
                resizablePanel.style.height = (startHeight + change - startY) + 'px';
            } else {
                resizablePanel.style.height = (startHeight + startY - change) + 'px';
            }
        }
       
    //    p.style.height = (startHeight + e.clientY - startY) + 'px';
    }
    
    function stopDrag(e) {
        document.documentElement.removeEventListener('mousemove', doDrag, false);
        document.documentElement.removeEventListener('mouseup', stopDrag, false);
    }

    // var p = document.querySelector('.media-panel'); // element to make resizable
    

    newBar.addEventListener('mousedown', initDrag, false);

    // resizer.addEventListener('click', function init() {
    //     p.removeEventListener('click', init, false);
    //     p.className = p.className + ' resizable';
    //     // var resizer = document.createElement('div');
    //     // resizer.className = 'resizer';
    //     // p.appendChild(resizer);
    //     resizer.addEventListener('mousedown', initDrag, false);
    //     // resizer.style.minWidth = "50px";
    //     // resizer.style.width = "50px";
    //     // resizer.style.flex = "1 1 50px";
    // }, false);
}