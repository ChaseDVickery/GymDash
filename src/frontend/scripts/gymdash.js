// import { resourceUsageUtils } from "./utils/usage.js";
import { testUtils } from "./utils/usage.js";

testUtils.testLog();

const tryBtn        = document.querySelector("#try-api-btn");
const tryBtnOut     = document.querySelector("#try-api-out");
const testBtn       = document.querySelector("#test-api-btn");
const testBtnOut    = document.querySelector("#test-api-out");
const resourceBtn       = document.querySelector("#resource-usage-btn");
const resourceBtnOut    = document.querySelector("#resource-usage-out");

const apiAddr = "http://127.0.0.1";
const apiPort = 8000;

function _apiURL() {
    return apiAddr + ":" + apiPort;
}
function apiURL(api_subaddr) {
    return _apiURL() + "/" + api_subaddr;
}

function call_random() {
    return fetch(apiURL("random"));
    // return fetch(apiURL("big-data1000");
    // return fetch(apiURL("big-data100000");
    // return fetch(apiURL("big-data1000000");
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
                // console.log(times);
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

tryBtn.addEventListener("click", getNumber);
testBtn.addEventListener("click", testNumberAPI);
resourceBtn.addEventListener("click", displayResourceUsage);





const resourceUsageUtils = (
    function() {
        // Constants
        const bToGiBConstant = 1 / Math.pow(2, 30);

        // DOM Elements
        const resourcePreviewElement= document.querySelector(".resource-preview");
        const resourceInfosElement  = resourcePreviewElement.querySelector(".resource-infos");
        const cpuPreviewMeter       = resourcePreviewElement.querySelector("#resource-preview-cpu");
        const memPreviewMeter       = resourcePreviewElement.querySelector("#resource-preview-mem");
        const dskPreviewMeter       = resourcePreviewElement.querySelector("#resource-preview-dsk");
        const gpumemPreviewMeter    = resourcePreviewElement.querySelector("#resource-preview-gpumem");
        const gpuloadPreviewMeter   = resourcePreviewElement.querySelector("#resource-preview-gpuload");
        const cpuPreviewText        = resourcePreviewElement.querySelector("#resource-preview-cpu-text");
        const memPreviewText        = resourcePreviewElement.querySelector("#resource-preview-mem-text");
        const dskPreviewText        = resourcePreviewElement.querySelector("#resource-preview-dsk-text");
        const gpumemPreviewText     = resourcePreviewElement.querySelector("#resource-preview-gpumem-text");
        const gpuloadPreviewText    = resourcePreviewElement.querySelector("#resource-preview-gpuload-text");
        
        const settingsBtn       = resourcePreviewElement.querySelector("#resource-preview-show-settings");
        const settingToggleAuto = resourcePreviewElement.querySelector("#resource-preview-toggle-auto");
        const settingToggleShow = resourcePreviewElement.querySelector("#resource-preview-toggle-show-values");
        const settingsWrapper   = resourcePreviewElement.querySelector(".settings-wrapper");


        // Internal Settings
        let autoUpdateResourcePreview       = true;
        let autoUpdateResourcePreviewTime   = 1000;     // Auto-update time in ms;
        let autoUpdateResourcePreviewID;
        
        let gpusAvailable;

        const fetchResourceUsageDetailed    = () => {return fetch(apiURL("resource-usage-detailed"));}
        const fetchResourceUsageSimple      = () => {return fetch(apiURL("resource-usage-simple"));}
        const fetchResourceUsageGPU         = () => {return fetch(apiURL("resource-usage-gpu"));}

        // Public Utilities
        const getResourceUsageDetailed = function() {
            return fetchResourceUsageDetailed()
                .then((response) => {
                    return response.json();
                });
        }
        const getResourceUsageSimple = function() {
            return fetchResourceUsageSimple()
                .then((response) => {
                    return response.json();
                });
        }
        const getResourceUsageGPU = function() {
            return fetchResourceUsageGPU()
                .then((response) => {
                    return response.json();
                });
        }
        const updateResourcePreview = function() {
            getResourceUsageSimple()
                .then((response) => {
                    const cpu = response.cpu_percent;
                    const mem = bytesToGibibytes(response.memory_total - response.memory_available);
                    const dsk = bytesToGibibytes(response.disk_total - response.disk_available);
                    cpuPreviewMeter.value = cpu;
                    memPreviewMeter.value = mem;
                    dskPreviewMeter.value = dsk;

                    cpuPreviewText.textContent = `CPU: ${(cpu).toFixed(1)}%`;
                    memPreviewText.textContent = `RAM: ${(mem).toFixed(1)}/${bytesToGibibytes(response.memory_total).toFixed(1)} GiB`;
                    dskPreviewText.textContent = `DSK: ${(dsk).toFixed(1)}/${bytesToGibibytes(response.disk_total).toFixed(1)} GiB`;
                    return response;
                });
            getResourceUsageGPU()
                .then((response) => {
                    const mem   = bytesToGibibytes(response.memory_total - response.memory_available);
                    const load  = response.load;
                    gpumemPreviewMeter.value    = mem;
                    gpuloadPreviewMeter.value   = load;

                    gpumemPreviewText.textContent = `VRAM: ${(mem).toFixed(1)}/${bytesToGibibytes(response.memory_total).toFixed(1)} GiB`;
                    gpuloadPreviewText.textContent = `LOAD: ${(load).toFixed(1)}%`;
                    return response;
                })
        }
        // General Settings
        const toggleSettings = function() {
            toggleElementShowing(settingsWrapper);
        }
        // Preview Settings
        const getPreviewAutoUpdate = function() { return autoUpdateResourcePreview; }
        const togglePreviewAutoUpdate = function() {
            autoUpdateResourcePreview = !autoUpdateResourcePreview;
            handlePreviewAutoUpdate();
            settingToggleAuto.checked = autoUpdateResourcePreview;
            return autoUpdateResourcePreview;
        }
        const setPreviewAutoUpdateTime = function(newTime) {
            autoUpdateResourcePreviewTime = newTime;
            handlePreviewAutoUpdate();
        }
        const togglePreviewShowValues = function() {
            const showing = toggleElementShowing(cpuPreviewText) &
                            toggleElementShowing(memPreviewText) &
                            toggleElementShowing(dskPreviewText);
            if (gpusAvailable) {
                toggleElementShowing(gpumemPreviewText);
                toggleElementShowing(gpuloadPreviewText);
            }
            settingToggleShow.checked = elementShowing(cpuPreviewText);
            return showing;
        }

        // Private Utilities
        const bytesToGibibytes = function(numBytes) {
            return numBytes * bToGiBConstant;
        }
        const setupSpaceMeter = function(meter, maxBytes) {
            meter.min = 0.0;
            meter.max = Math.round(bytesToGibibytes(maxBytes));
        }
        const handlePreviewAutoUpdate = function() {
            autoUpdateResourcePreviewID = handleAutoUpdateChange(
                autoUpdateResourcePreview,
                updateResourcePreview,
                autoUpdateResourcePreviewID,
                autoUpdateResourcePreviewTime
            );
        }
        const handleAutoUpdateChange = function(shouldUpdate, intervalCallback, invervalID, intervalTime) {
            if (invervalID) { clearInterval(invervalID); }
            if (shouldUpdate) {
                return setInterval(intervalCallback, intervalTime);
            } else {
                return undefined;
            }
        }
        const toggleElementShowing = function(element) {
            const hidden = element.style.display === "none";
            if (hidden) {
                element.style.display = "block";
            } else {
                element.style.display = "none";
            }
            // Should be toggled by here
            return !hidden;
        }
        const elementHidden = (element) => {return element.style.display === "none";}
        const elementShowing = (element) => {return !elementHidden(element);}


        // Setup resource meter previews
        getResourceUsageSimple()
            .then((response) => {
                setupSpaceMeter(memPreviewMeter, response.memory_total);
                return response;
            })
            .then((response) => {
                setupSpaceMeter(dskPreviewMeter, response.disk_total);
                return response;
            })
            .then((response) => {
                cpuPreviewMeter.min = 0.0;
                cpuPreviewMeter.max = 100.0;
                return response;
            })
            .then((response) => {
                updateResourcePreview();
                return response;
            });
        getResourceUsageGPU()
            .then((response) => {
                console.log("We have " + response.gpu_count + " gpus");
                // Hide GPU lines if we have none
                // Show GPU lines if we have some
                if (response.gpu_count === 0) {
                    gpusAvailable = false;
                    toggleElementShowing(gpumemPreviewMeter.parentElement);
                    toggleElementShowing(gpuloadPreviewMeter.parentElement);
                } else {
                    gpusAvailable = true;
                    gpumemPreviewMeter.min = 0;
                    gpumemPreviewMeter.max = Math.round(bytesToGibibytes(response.memory_total));
                    gpuloadPreviewMeter.min = 0.0;
                    gpuloadPreviewMeter.max = 100.0;
                }
                return response;
            });
        handlePreviewAutoUpdate();
        // Setup settings menu
        toggleSettings();
        togglePreviewAutoUpdate();
        togglePreviewAutoUpdate();
        togglePreviewShowValues();
        togglePreviewShowValues();

        settingToggleShow.checked = elementShowing(cpuPreviewText);
        
        resourceInfosElement.addEventListener("click", (e) => {
            toggleSettings();
        });
        settingToggleAuto.addEventListener("click", (e) => {
            togglePreviewAutoUpdate();
            // settingToggleAuto.checked = autoUpdateResourcePreview;
        });
        settingToggleShow.addEventListener("click", (e) => {
            togglePreviewShowValues();
            // settingToggleAuto.checked = autoUpdateResourcePreview;
            // settingToggleShow.checked = !togglePreviewShowValues();
        });


        return {
            getResourceUsageDetailed, 
            getResourceUsageSimple,
            updateResourcePreview,
            // Preview auto update settings
            getPreviewAutoUpdate,
            togglePreviewAutoUpdate,
            setPreviewAutoUpdateTime
        };
    }
)();