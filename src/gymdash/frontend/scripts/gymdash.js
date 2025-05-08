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
const defaultSimProgressUpdateInterval = 5000;  // (ms)
const defaultTimeout = 2.5; // (s)
const noID = "00000000-0000-0000-0000-000000000000"; // (str(UUID))

// Structures
// sim_selections store information
let sim_selections = {};
// allData stores all the data retrieved from the backend
// Maps in the following way:
//      simID -> {
//          "scalars" -> {stat_key1_s -> [], ...},
//          "images" -> {stat_key1_i -> [], ...},
//          "audio" -> {stat_key1_a -> [], ...}
//      }
let allData = {};

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
            // if (useKey) {
            //     return data.filter((datum) => datum[this.key] === filterValue)
            // } else {
            //     return data.filter((datum) => datum === filterValue)
            // }
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

function getActiveSelections() {

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
function getSelectedData() {
    const selectedSelections = getSelectedSelections();
    const selectedData = {};
    for (const id in selectedSelections) {
        selectedData[id] = allData[id];
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
    // const selectionOptions = document.querySelectorAll(".sim-selection-checkbox");
    // const randomSelection = selectionOptions[Math.floor(Math.random()*selectionOptions.length)];
    // const simID = randomSelection.id;
    const dataRetrievalPromises = [];
    const allDataReports = [];
    // const selectionOptions = document.querySelectorAll(".sim-selection-checkbox");
    const selectionOptions = getSelectedSelections();
    // for (let i = 0; i < selectionOptions.length; i++) {
    for (const simID in selectionOptions){
        // const simID = selectionOptions[i].id;
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
            // allData report
            for (let j = 0; j < allDataReports.length; j++) {
                const simID = allDataReports[j].simID;
                if (!Object.hasOwn(allData, simID)) {
                    // allData[simID] = dataUtils.createEmptyDataReport(simID);
                    allData[simID] = new dataUtils.DataReport(simID);
                }
                // dataUtils.dataReportUnion(allData[simID], allDataReports[j]);
                allData[simID].addDataReport(allDataReports[j]);
            }
            console.log("ALL DATA");
            console.log(allData);
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

function updateAllSimSelectionProgress() {
    // Iterates all incomplete sim selections and queries their progress
    for (const [simID, simSelection] of Object.entries(sim_selections)) {
        updateSimSelectionProgress(simID, simSelection);
    }
}
function updateSimSelectionProgress(simID, simSelection) {
    const meter = simSelection.querySelector(".radial-meter")
    // if (meter.classList.contains("complete")) { return; }
    const is_done = meter.classList.contains("complete");
    if (is_done) { return Promise.resolve(); }
    const outer = meter.querySelector(".outer")
    return queryProgress(simID, is_done)
        .then((info) => {
            console.log(info);
            if (info.is_done) {
                meter.classList.add("complete");
                meter.classList.remove("incomplete");
                if (info.cancelled || info.failed) {
                    meter.classList.add("fail");
                } else {
                    meter.classList.add("success");
                }
            }
            if (Object.hasOwn(info, "progress")) {
                if (info.progress[1] === 0) { return info; }
                outer.style.setProperty("--prog", `${100*info.progress[0]/info.progress[1]}%`);
            }
        })
        .catch((error) => {
            console.error(`Update sim selection progress error: ${error}`)
        });
}

function refreshSimulationSidebar() {
    // Clear all the current sim selections and remove from DOM
    const selections = getAllSelections();
    const selected = getSelectedSelections();
    for (const id in selections) {
        selections[id].remove();
    }
    sim_selections = {};
    // Fetch sim history in backend DB
    fetch(apiURL("get-sims-history"))
    .then((response) => response.json())
    .then((infos) => {
        // Should be list of StartedSimulationInfo
        console.log(infos);
        infos.forEach(info => {
            const simID = info.sim_id;
            const config = info.config;
            if (!validID(simID)) {
                return info;
            }
            const startChecked = Object.hasOwn(selected, simID);
            const newSelection = createSimSelection(config, simID, startChecked);
            // Note: Check to store the simulation in sim_selections because
            // we only want running simulations in sim_selections.
            const meter = newSelection.querySelector(".radial-meter")
            if (info.is_done) {
                meter.classList.add("complete");
                meter.classList.remove("incomplete");
                if (info.cancelled || info.failed) {
                    meter.classList.add("fail");
                } else {
                    meter.classList.add("success");
                }
            } else {
                sim_selections[simID] = newSelection;
            }
            console.log(info);
        });
        return infos;
    })
    .catch((error) => {
        console.error("Error: " + error);
    });
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
    const newSelection = prefabSimSelectBox.cloneNode(true);
    // Set up new selection box
    const selectionID = `${simID}`;
    newSelection.classList.remove("prefab");
    const label = newSelection.querySelector("label");
    const input = newSelection.querySelector(".sim-selection-checkbox")
    input.id            = selectionID;
    input.checked       = startChecked;
    label.htmlFor       = selectionID;
    label.textContent   = config.name;
    simSidebar.appendChild(newSelection);
    // Set up cancel button
    const cancelButton = newSelection.querySelector(".cancel-sim-button");
    cancelButton.addEventListener("click", stopSimulationFromSelection.bind(null, newSelection));
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
        // Store new simulation in tracker
        sim_selections[simID] = newSelection;
        console.log(info);
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
        // Store new simulation in tracker
        sim_selections[simID] = newSelection;
        console.log(info);
        return info;
    })
    .catch((error) => {
        console.error("Error: " + error);
    });
}
function stopSimulationFromSelection(simSelection) {
    
    const input = simSelection.querySelector(".sim-selection-checkbox")
    const meter = simSelection.querySelector(".radial-meter")
    const simID = input.id;
    // Set stopping visuals and remove from sim_selections
    delete sim_selections[simID];
    meter.classList.add("cancelling");
    stopSimulation(simID)
        .then((response) => {
            console.log(`Done calling stop simulation on ${simID}`);
            
            updateSimSelectionProgress(simID, simSelection)
                .then((response) => {
                    // Put back in simSelection and stop cancellation visual
                    sim_selections[simID] = simSelection;
                    meter.classList.remove("cancelling");
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
    for (const [key, simSelection] of Object.entries(sim_selections)) {
        const meter = simSelection.querySelector(".radial-meter")
        const simID = key;
        // Set stopping visuals and remove from sim_selections
        delete sim_selections[simID];
        meter.classList.add("cancelling");
    }
    fetch(apiURL("delete-all-sims"))
        .then((response) => { return response.json(); })
        .then((info) => {
            sim_selections = {};
            allData = {};
            refreshSimulationSidebar();
        })
        .catch((error) => { console.error(`Error while deleting all simulations: ${error}`)});
}
function deleteSelectedSimulations() {
    console.log("deleteSelectedSimulations");
    // Visually indicate all running sims as cancelling
    const simIDs = [];
    for (const [key, simSelection] of Object.entries(getAllSelections())) {
        const checkbox = simSelection.querySelector(".sim-selection-checkbox");
        const meter = simSelection.querySelector(".radial-meter")
        const simID = key;
        if (checkbox.checked) {
            simIDs.push(simID);
            // Set stopping visuals and remove from sim_selections
            delete sim_selections[simID];
            meter.classList.add("cancelling");
            console.log("deleting " + simID);
        }
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
        sim_selections = {};
        allData = {};
        refreshSimulationSidebar();
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



// Setup intervals
setInterval(updateAllSimSelectionProgress, defaultSimProgressUpdateInterval);


refreshSimulationSidebar();
openTab(null, "tab-analyze");


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
    const key = "rollout/ep_rew_mean";
    // const key = "my_number";

    clearMainPlot();

    const condense = true;
    const selectedData = getSelectedData();

    const plot = vizUtils.createLinePlotForKey(key, selectedData);
    const detailsPlot = vizUtils.createLinePlotForKey(key, selectedData);

    plot.addAllMMIs(selectedData, onClickMMI, condense);
    detailsPlot.addAllMMIs(selectedData, onClickMMI, condense);
    plot.addBrushX(function(event) {
        // plot.refresh();
        detailsPlot.updatePlot(event, plot);
    }, "brush");
    // plot.addBrushX(plot.clearBrush.bind(plot), "end");

    // const width = vizUtils.plotWidth;
    // const height = vizUtils.plotHeight;
    // plot.brushX = d3.brushX()
    //     .extent([60, 30], [width, height-30])
    //     .on("end", function(e) {console.log(e); detailsPlot.updatePlot(e)});
    // plot.svg.call(
    //     plot.brushX
    // );

    // plot.addBrushX(
    //     function(e) {
    //         detailsPlot.updatePlot(e);
    //     }
    // );

    // let detailsPlot = vizUtils.createLinePlotForKey(key, selectedData);
    // plot.addBrushX(function() {
    //     line.select(".brush").call(brush.move, null)
    //     detailsPlot.
    // })
    
    d3.select("#plots-area").append(() => plot.svg.node());
    d3.select("#plots-area").append(() => detailsPlot.svg.node());
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