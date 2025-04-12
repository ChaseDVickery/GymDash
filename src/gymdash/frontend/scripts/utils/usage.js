import { apiURL } from "./api_link.js";
import { byteConversions as bc } from "./conversions.js";

const resourceUsageUtils = (
    function() {
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
        const areGPUsAvailable = function() {
            return gpusAvailable;
        }


        // Setup resource meter previews
        getResourceUsageGPU()
            .then((response) => {
                console.log("We have " + response.gpu_count + " gpus");
                // Hide GPU lines if we have none
                // Show GPU lines if we have some
                if (response.gpu_count === 0) {
                    gpusAvailable = false;
                } else {
                    gpusAvailable = true;
                }
                return response;
            });

        return {
            getResourceUsageDetailed, 
            getResourceUsageSimple,
            getResourceUsageGPU,
            areGPUsAvailable
        };
    }
)();


const resourceUsageDisplayUtils = (
    function() {
        const setupResourceUsageDisplay = function(rootResourcePreviewElement=null, miniaturize=false) {
            // DOM Elements
            let resourcePreviewElement = rootResourcePreviewElement;
            if (resourcePreviewElement === null) {
                resourcePreviewElement= document.querySelector(".resource-preview");
            }
            if (resourcePreviewElement  === null) {
                console.error(`The selector ".resource-preview" could not be found in the DOM. Unable to setup resource usage display.`);
                return;
            }
            const resourceInfosElement  = resourcePreviewElement.querySelector(".resource-infos");
            const cpuPreviewMeter       = resourcePreviewElement.querySelector(".resource-preview-cpu");
            const memPreviewMeter       = resourcePreviewElement.querySelector(".resource-preview-mem");
            const dskPreviewMeter       = resourcePreviewElement.querySelector(".resource-preview-dsk");
            const gpumemPreviewMeter    = resourcePreviewElement.querySelector(".resource-preview-gpumem");
            const gpuloadPreviewMeter   = resourcePreviewElement.querySelector(".resource-preview-gpuload");
            const cpuPreviewText        = resourcePreviewElement.querySelector(".resource-preview-cpu-text");
            const memPreviewText        = resourcePreviewElement.querySelector(".resource-preview-mem-text");
            const dskPreviewText        = resourcePreviewElement.querySelector(".resource-preview-dsk-text");
            const gpumemPreviewText     = resourcePreviewElement.querySelector(".resource-preview-gpumem-text");
            const gpuloadPreviewText    = resourcePreviewElement.querySelector(".resource-preview-gpuload-text");
            
            const settingToggleAuto         = resourcePreviewElement.querySelector(".resource-preview-toggle-auto");
            const settingToggleShow         = resourcePreviewElement.querySelector(".resource-preview-toggle-show-values");
            const settingToggleValueLabels  = resourcePreviewElement.querySelector(".resource-preview-toggle-show-value-labels");
            const settingSliderRefreshTime  = resourcePreviewElement.querySelector(".resource-preview-refresh-time");
            const settingsWrapper           = resourcePreviewElement.querySelector(".settings-wrapper");

            // Perform check before doing anything else
            if (
                resourceInfosElement    === null ||
                cpuPreviewMeter         === null ||
                memPreviewMeter         === null ||
                dskPreviewMeter         === null ||
                gpumemPreviewMeter      === null ||
                gpuloadPreviewMeter     === null ||
                cpuPreviewText          === null ||
                memPreviewText          === null ||
                dskPreviewText          === null ||
                gpumemPreviewText       === null ||
                gpuloadPreviewText      === null ||
                settingToggleAuto       === null ||
                settingToggleShow       === null ||
                settingToggleValueLabels=== null ||
                settingSliderRefreshTime=== null ||
                settingsWrapper         === null
            ) {
                console.error(`One or more of the following selectors could not be found in the DOM. Unable to setup resource usage display:
                .resource-preview .resource-infos
                .resource-preview .resource-preview-cpu
                .resource-preview .resource-preview-mem
                .resource-preview .resource-preview-dsk
                .resource-preview .resource-preview-gpumem
                .resource-preview .resource-preview-gpuload
                .resource-preview .resource-preview-cpu-text
                .resource-preview .resource-preview-mem-text
                .resource-preview .resource-preview-dsk-text
                .resource-preview .resource-preview-gpumem-text
                .resource-preview .resource-preview-gpuload-text
                .resource-preview .resource-preview-toggle-auto
                .resource-preview .resource-preview-toggle-show-values
                .resource-preview .resource-preview-toggle-show-value-labels
                .resource-preview .resource-preview-refresh-time
                .resource-preview .settings-wrapper
                `);
                return;
            }


            // Internal Settings
            let autoUpdateResourcePreview       = false;
            let autoUpdateResourcePreviewTime   = 1000;     // Auto-update time in ms;
            let autoUpdateResourcePreviewID;
            let showResourceValues              = true;
            let showResourceLabels              = true;

            // Public Utilities
            const updateResourcePreview = function() {
                resourceUsageUtils.getResourceUsageSimple()
                    .then((response) => {
                        const cpu = response.cpu_percent;
                        const mem = bc.B2GiB(response.memory_total - response.memory_available);
                        const dsk = bc.B2GiB(response.disk_total - response.disk_available);
                        cpuPreviewMeter.value = cpu;
                        memPreviewMeter.value = mem;
                        dskPreviewMeter.value = dsk;

                        const cpuValueString = showResourceValues ? `${(cpu).toFixed(1)}%` : "";
                        const memValueString = showResourceValues ? `${(mem).toFixed(1)}/${bc.B2GiB(response.memory_total).toFixed(1)} GiB` : "";
                        const dskValueString = showResourceValues ? `${(dsk).toFixed(1)}/${bc.B2GiB(response.disk_total).toFixed(1)} GiB` : "";

                        cpuPreviewText.textContent = `${showResourceLabels ? "CPU: ": ""}${cpuValueString}`;
                        memPreviewText.textContent = `${showResourceLabels ? "RAM: ": ""}${memValueString}`;
                        dskPreviewText.textContent = `${showResourceLabels ? "DSK: ": ""}${dskValueString}`;
                        return response;
                    });
                    resourceUsageUtils.getResourceUsageGPU()
                    .then((response) => {
                        const mem   = bc.B2GiB(response.memory_total - response.memory_available);
                        const load  = response.load;
                        gpumemPreviewMeter.value    = mem;
                        gpuloadPreviewMeter.value   = load;

                        const gpumemValueString  = showResourceValues ? `${(mem).toFixed(1)}/${bc.B2GiB(response.memory_total).toFixed(1)} GiB` : "";
                        const gpuloadValueString = showResourceValues ? `${(load).toFixed(1)}%` : "";

                        gpumemPreviewText.textContent   = `${showResourceLabels ? "VRAM: " : ""}${gpumemValueString}`;
                        gpuloadPreviewText.textContent  = `${showResourceLabels ? "LOAD: " : ""}${gpuloadValueString}`;
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
            const setRefreshTime = function(newTimeMS) {
                autoUpdateResourcePreviewTime = Number(newTimeMS);
                handlePreviewAutoUpdate();
            }

            function manageResourceLabels() {
                const wasShowing = elementShowing(cpuPreviewText);
                const shouldShow = (showResourceLabels || showResourceValues);
                const shouldHide = !showResourceLabels && !showResourceValues;
                const isMini     = showResourceLabels && !showResourceValues;
                if (wasShowing && shouldHide) {
                    toggleElementShowing(cpuPreviewText);
                    toggleElementShowing(memPreviewText);
                    toggleElementShowing(dskPreviewText);
                    setElementShowing(gpumemPreviewText, elementShowing(cpuPreviewText));
                    setElementShowing(gpuloadPreviewText, elementShowing(cpuPreviewText));
                }
                else if (!wasShowing && shouldShow) {
                    toggleElementShowing(cpuPreviewText);
                    toggleElementShowing(memPreviewText);
                    toggleElementShowing(dskPreviewText);
                    setElementShowing(gpumemPreviewText, elementShowing(cpuPreviewText));
                    setElementShowing(gpuloadPreviewText, elementShowing(cpuPreviewText));
                }
                if (isMini) {
                    cpuPreviewText.classList.add("mini");
                    memPreviewText.classList.add("mini");
                    dskPreviewText.classList.add("mini");
                    gpumemPreviewText.classList.add("mini");
                    gpuloadPreviewText.classList.add("mini");
                } else {
                    cpuPreviewText.classList.remove("mini");
                    memPreviewText.classList.remove("mini");
                    dskPreviewText.classList.remove("mini");
                    gpumemPreviewText.classList.remove("mini");
                    gpuloadPreviewText.classList.remove("mini");
                }
            }
            const togglePreviewShowValueLabels = function() {
                showResourceLabels = !showResourceLabels;
                settingToggleValueLabels.checked = showResourceLabels;
                updateResourcePreview();
                manageResourceLabels();
                return showResourceLabels;
            }
            const togglePreviewShowValues = function() {
                showResourceValues = !showResourceValues;
                settingToggleShow.checked = showResourceValues;
                updateResourcePreview();
                manageResourceLabels();
                return showResourceValues;
            }

            // Private Utilities
            const setupSpaceMeter = function(meter, maxBytes) {
                meter.min = 0.0;
                meter.max = Math.round(bc.B2GiB(maxBytes));
                // meter.low = Math.round(bc.B2GiB(maxBytes) * 0.60);
                // meter.high = Math.round(bc.B2GiB(maxBytes) * 0.80);
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
                element.classList.toggle("hidden");
                const hidden = element.classList.contains("hidden");
                // Should be toggled by here
                return !hidden;
            }
            const setElementShowing = function(element, show) {
                if (show) { element.classList.remove("hidden"); }
                else { element.classList.add("hidden"); }
            }
            const elementHidden = (element) => {return element.classList.contains("hidden");}
            const elementShowing = (element) => {return !elementHidden(element);}


            // Setup resource meter previews
            resourceUsageUtils.getResourceUsageSimple()
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
                    cpuPreviewMeter.low = Math.round(100 * 0.60);
                    cpuPreviewMeter.high = Math.round(100 * 0.80);
                    return response;
                })
                .then((response) => {
                    updateResourcePreview();
                    return response;
                });
            resourceUsageUtils.getResourceUsageGPU()
                .then((response) => {
                    // Hide GPU lines if we have none
                    // Show GPU lines if we have some
                    if (response.gpu_count === 0) {
                        toggleElementShowing(gpumemPreviewMeter.parentElement);
                        toggleElementShowing(gpuloadPreviewMeter.parentElement);
                    } else {
                        gpumemPreviewMeter.min = 0;
                        gpumemPreviewMeter.max = Math.round(bc.B2GiB(response.memory_total));
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
            if (!miniaturize) { togglePreviewShowValues(); }
            togglePreviewShowValueLabels();
            if (!miniaturize) { togglePreviewShowValueLabels(); }
            
            resourceInfosElement.addEventListener("click", (e) => {
                toggleSettings();
            });
            settingToggleAuto.addEventListener("click", (e) => {
                togglePreviewAutoUpdate();
            });
            settingToggleShow.addEventListener("click", (e) => {
                togglePreviewShowValues();
            });
            settingToggleValueLabels.addEventListener("click", (e) => {
                togglePreviewShowValueLabels();
            });
            settingSliderRefreshTime.addEventListener("change", (e) => {
                setRefreshTime(1000*Number(e.target.value));
            });
        }
        


        return {
            setupResourceUsageDisplay
        };
    }
)();

export { resourceUsageUtils, resourceUsageDisplayUtils };