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
        const setupResourceUsageDisplay = function() {
            // DOM Elements
            const resourcePreviewElement= document.querySelector(".resource-preview");
            if (resourcePreviewElement  === null) {
                console.error(`The selector ".resource-preview" could not be found in the DOM. Unable to setup resource usage display.`);
                return;
            }
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
            
            const settingToggleAuto         = resourcePreviewElement.querySelector("#resource-preview-toggle-auto");
            const settingToggleShow         = resourcePreviewElement.querySelector("#resource-preview-toggle-show-values");
            const settingSliderRefreshTime  = resourcePreviewElement.querySelector("#resource-preview-refresh-time");
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
                settingSliderRefreshTime=== null ||
                settingsWrapper         === null
            ) {
                console.error(`One or more of the following selectors could not be found in the DOM. Unable to setup resource usage display:
                .resource-preview .resource-infos
                .resource-preview #resource-preview-cpu
                .resource-preview #resource-preview-mem
                .resource-preview #resource-preview-dsk
                .resource-preview #resource-preview-gpumem
                .resource-preview #resource-preview-gpuload
                .resource-preview #resource-preview-cpu-text
                .resource-preview #resource-preview-mem-text
                .resource-preview #resource-preview-dsk-text
                .resource-preview #resource-preview-gpumem-text
                .resource-preview #resource-preview-gpuload-text
                .resource-preview #resource-preview-toggle-auto
                .resource-preview #resource-preview-toggle-show-values
                .resource-preview #resource-preview-refresh-time
                .resource-preview .settings-wrapper
                `);
                return;
            }


            // Internal Settings
            let autoUpdateResourcePreview       = true;
            let autoUpdateResourcePreviewTime   = 1000;     // Auto-update time in ms;
            let autoUpdateResourcePreviewID;

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

                        cpuPreviewText.textContent = `CPU: ${(cpu).toFixed(1)}%`;
                        memPreviewText.textContent = `RAM: ${(mem).toFixed(1)}/${bc.B2GiB(response.memory_total).toFixed(1)} GiB`;
                        dskPreviewText.textContent = `DSK: ${(dsk).toFixed(1)}/${bc.B2GiB(response.disk_total).toFixed(1)} GiB`;
                        return response;
                    });
                    resourceUsageUtils.getResourceUsageGPU()
                    .then((response) => {
                        const mem   = bc.B2GiB(response.memory_total - response.memory_available);
                        const load  = response.load;
                        gpumemPreviewMeter.value    = mem;
                        gpuloadPreviewMeter.value   = load;

                        gpumemPreviewText.textContent = `VRAM: ${(mem).toFixed(1)}/${bc.B2GiB(response.memory_total).toFixed(1)} GiB`;
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
            const setRefreshTime = function(newTimeMS) {
                autoUpdateResourcePreviewTime = Number(newTimeMS);
                handlePreviewAutoUpdate();
            }
            const togglePreviewShowValues = function() {
                const showing = toggleElementShowing(cpuPreviewText) &
                                toggleElementShowing(memPreviewText) &
                                toggleElementShowing(dskPreviewText);
                if (resourceUsageUtils.areGPUsAvailable()) {
                    toggleElementShowing(gpumemPreviewText);
                    toggleElementShowing(gpuloadPreviewText);
                }
                settingToggleShow.checked = elementShowing(cpuPreviewText);
                return showing;
            }

            // Private Utilities
            const setupSpaceMeter = function(meter, maxBytes) {
                meter.min = 0.0;
                meter.max = Math.round(bc.B2GiB(maxBytes));
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