import { apiURL } from "./api_link.js";
import { mediaUtils } from "./media_utils.js";

const dataUtils = (
    function() {

        class DataReport {
            static SCALAR = "scalars";
            static IMAGE = "images";
            static AUDIO = "audio";
            static VIDEO = "videos";

            constructor(simID) {
                this.simID = simID;
                this.id = simID;
                // Key sets provide a fast way to check whether
                // a certain key is of a certain (media) type.
                this.scalar_keys = new Set();
                this.image_keys = new Set();
                this.audio_keys = new Set();
                this.video_keys = new Set();
                // Meta structures contain metadata objects
                // including type information for each key
                this.meta = new Map();
                // Object mapping keys to a data array
                // { key -> [{whatever form the data points take}]}
                this.data = new Map();
            }

            static types() {
                return [
                    SCALAR,
                    IMAGE,
                    AUDIO,
                    VIDEO,
                ];
            }

            /**
             * Combines the data array otherData into the
             * data array in the dataReport's key. This
             * assumes the incoming array is in the correct
             * format and of the same type.
             * 
             * @param {string} key 
             * @param {Array} otherData 
             * @returns 
             */
            #assimilateDataInto(key, otherData) {
                // Sort incoming data
                otherData.sort((a,b) => {return a.step-b.step;});
                console.log("otherdata " + key);
                console.log(otherData);

                if (!this.data.has(key)) {
                    this.data.set(key, []);
                }

                // Insert the new data in sorted order
                const d1 = this.data.get(key);
                const d2 = otherData;
                // Some basic checks before getting into the weeds.
                // If either is empty, then we just insert one into
                // the other.
                if (d1.length < 1 || d2.length < 1) {
                    d1.push(...d2);
                    return;
                }
                // The typical use case means that the first value of
                // dr2 is USUALLY greater than the greatest/last value
                // of dr1, so we can just push all values right to the end.
                if (d1[d1.length-1].step < d2[0].step) {
                    d1.push(...d2);
                    return;
                }
                // Iterate all the datapoints of 2nd report's keys
                let dr1_idx = 0;
                let dr2_idx = 0;
                while (dr2_idx < d2.length) {
                    // If we are out of bounds of dr1, then
                    // we know to just start inserting at the end.
                    if (dr1_idx >= d1.length) {
                        d1.push(d2[dr2_idx]);
                        dr2_idx += 1;
                        continue;
                    }
                    // If current insert value is less than the current
                    // value at dr1
                    if (d2[dr2_idx].step < d1[dr1_idx].step) {
                        d1.splice(dr1_idx, 0, d2[dr2_idx]);
                        // Must push idx forward by 1 to keep place
                        dr1_idx += 1;
                        dr2_idx += 1;
                    }
                    // If current insert value is EQUAL, then
                    // we REPLACE the value at dr1
                    else if (d2[dr2_idx].step === d1[dr1_idx].step) {
                        d1[dr1_idx] = d2[dr2_idx];
                        dr2_idx += 1;
                    }
                    else {
                        dr1_idx += 1;
                    }
                }
            }

            // ADD DATA TO REPORT
            #addData(key, data, meta, key_set) {
                key_set.add(key);
                if (!this.meta.has(key) && meta) { this.meta.set(key, meta); }
                this.#assimilateDataInto(key, data);
            }
            addScalarData(key, data, meta=null) {
                if (!meta) { meta = {}; }
                meta.type = DataReport.SCALAR;
                this.#addData(key, data, meta, this.scalar_keys);
            }
            addImageData(key, data, meta=null) {
                if (!meta) { meta = {}; }
                meta.type = DataReport.IMAGE;
                this.#addData(key, data, meta, this.image_keys);
            }
            addAudioData(key, data, meta=null) {
                if (!meta) { meta = {}; }
                meta.type = DataReport.AUDIO;
                this.#addData(key, data, meta, this.audio_keys);
            }
            addVideoData(key, data, meta=null) {
                if (!meta) { meta = {}; }
                meta.type = DataReport.VIDEO;
                this.#addData(key, data, meta, this.video_keys);
            }
            addDataOfType(key, data, meta=null, dataType) {
                console.log(key + " metafile:");
                console.log(meta);
                console.log(data);
                console.log(dataType);
                if (dataType === "scalar" || dataType === "scalars") {
                    this.addScalarData(key, data, meta);
                }
                else if (dataType === "image" || dataType === "images") {
                    this.addImageData(key, data, meta);
                }
                else if (dataType === "audio" || dataType === "audios") {
                    this.addAudioData(key, data, meta);
                }
                else if (dataType === "video" || dataType === "videos") {
                    this.addVideoData(key, data, meta);
                }
                else {
                    console.error("Cannot add data of because type '" + dataType + "' does not match valid type");
                }
            }
            addDataReport(otherReport) {
                for (const key of otherReport.meta.keys()) {
                    this.addDataOfType(
                        key,
                        otherReport.data.get(key),
                        otherReport.meta.get(key),
                        otherReport.meta.get(key).type
                    );
                }
            }

            // QUERY DATA REPORT
            has(key) {
                return this.data.has(key);
            }
            getKeyType(key) {
                if (!this.meta.has(key)) { return undefined; }
                return this.meta.get(key).type;
            }
            isScalar(key) { return this.scalar_keys.has(key); }
            isImage(key) { return this.image_keys.has(key); }
            isAudio(key) { return this.audio_keys.has(key); }
            isVideo(key) { return this.video_keys.has(key); }
            getMediaKeys() {
                return new Set([
                    ...this.image_keys,
                    ...this.audio_keys,
                    ...this.video_keys
                ]);
            }

            getData(key) {
                if (!this.data.has(key)) { return []; }
                return this.data.get(key);
            }
            getScalar(key) {
                if(this.isScalar(key)) { return this.getData(key); }
                else { return []; }
            }
            getImage(key) {
                if(this.isImage(key)) { return this.getData(key); }
                else { return []; }
            }
            getAudio(key) {
                if(this.isAudio(key)) { return this.getData(key); }
                else { return []; }
            }
            getVideo(key) {
                if(this.isVideo(key)) { return this.getData(key); }
                else { return []; }
            }
        }

        const fetchAllRecentValues    = () => {return fetch(apiURL(`all-recent-scalars`));}
        const fetchAllRecentImages    = () => {return fetch(apiURL(`all-recent-images`), { responseType: 'blob' });}
        const fetchAllRecentMediaForSimulation    = (sim_id) => {return fetch(apiURL(`sim-recent-media`), {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            responseType: 'blob',
            body: JSON.stringify({id: sim_id})
        });}
        const fetchRecentForSimulation    = (sim_id, tags=[], keys=[], exclusion_mode=false) => {return fetch(apiURL(`sim-data-recent`), {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            responseType: 'blob',
            body: JSON.stringify({
                id: sim_id,
                tags: tags,
                keys: keys,
                exclusion_mode: exclusion_mode
            })
        });}
        const fetchAllForSimulation    = (sim_id, tags=[], keys=[], exclusion_mode=false) => {return fetch(apiURL(`sim-data-all`), {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            responseType: 'blob',
            body: JSON.stringify({
                id: sim_id,
                tags: tags,
                keys: keys,
                exclusion_mode: exclusion_mode
            })
        });}
        // const fetchAllRecentValues    = () => {return fetch(apiURL(`read-key/?exp_key=${encodeURIComponent("tb\\stock\\train")}&key=${encodeURIComponent("rollout/ep_rew_mean")}&recent=True`));}

        // Public Utilities
        const createEmptyDataReport = function(simulationID) {
            return {
                simID: simulationID,
                media: {
                    "scalars": {},
                    "images": {},
                    "audio": {},
                }
            }
        }
        const getAllNewScalars = function() {
            return fetchAllRecentValues()
                .then((response) => {
                    console.log(response);
                    return response.json();
                });
        }
        const generateMediaReportFromZip = function(blob) {
            // Create zip object
            const zip = new JSZip();
            const indexFilename = "index.json";
            // Load zip data
            const loader = zip.loadAsync(blob)
                .then((zip_contents) => {
                    // Return promise processing contents...
                    return zip.file(indexFilename).async("string").then((index_contents) => {
                        const index = JSON.parse(index_contents);
                        console.log(index);
                        // Don't need to iterate the zip contents
                        // We just iterate through the index file instead
                        const streamer = index.streamer_key;
                        const fileMetadata = [];
                        const filePromises = [];
                        for (let media_filename in index.metadata) {
                            fileMetadata.push(index.metadata[media_filename]);
                            filePromises.push(zip.file(media_filename).async("arraybuffer"));
                        }
                        // Wait for all files to load, then...
                        return Promise.all(filePromises)
                            .then((files) => {
                                // mediaReport object contains the finalized
                                // media source URLs, the steps for each media url,
                                // and the simulation ID associated
                                const mediaReport = {
                                    simID: index.sim_id,
                                    media: {}   // Object mapping media types to array of url+step objects
                                };
                                console.log(mediaReport);
                                // Fill the media report media object with
                                // mappings from each unique media type
                                const unique_types = new Set(fileMetadata.map(x => x.mimetype));
                                console.log(unique_types)
                                unique_types.forEach(t => mediaReport.media[t] = []);
                                console.log(mediaReport);
                                // Iterate files and create media src url for them
                                for (let i = 0; i < files.length; i++) {
                                    const file = files[i];
                                    const meta = fileMetadata[i];
                                    const mediaSrc = mediaUtils.createMediaSourceURL(meta.mimetype, mediaUtils.conversionUtils.binaryToBase64(file));
                                    // Push new object representing media with
                                    // the media url and the step
                                    mediaReport.media[meta.mimetype].push({
                                        value: mediaSrc,
                                        step: meta.step
                                    });
                                }
                                console.log(mediaReport);
                                // Sort each list by ascending step number
                                for (const t of unique_types) {
                                    mediaReport.media[t].sort((a, b) => { return a.step - b.step; })
                                }
                                console.log(mediaReport);
                                // Return promise of media report
                                return Promise.resolve(mediaReport);
                            });
                    });
                });
            // Return promise of mediaReport
            return loader;
        }
        const getAllNewImages = function() {
            return fetchAllRecentImages()
                .then((response) => {
                    // The backend already sent a zip blob,
                    // we just need to interpret it as a zip.
                    console.log("Done fetching all recent images");
                    const blob = response.blob();
                    // Return promise of media report
                    return generateMediaReportFromZip(blob);
                })
                .catch((error) => {
                    console.error(`Problem while resolving getAllNewImages: ${error}`);
                });
        }
        const getSimNewMedia = function(simID) {
            return fetchAllRecentMediaForSimulation(simID)
                .then((response) => {
                    // The backend already sent a zip blob,
                    // we just need to interpret it as a zip.
                    console.log("Done fetching all recent simulation media");
                    const blob = response.blob();
                    // Return promise of media report
                    return generateMediaReportFromZip(blob);
                })
                .catch((error) => {
                    console.error(`Problem while resolving getAllNewImages: ${error}`);
                });
        }

        const processMediaFilesToReport = function(mediaReport, mediaType, filesArr, metadataArr, toSrc=null) {
            // Create a set for all keys seen in the type
            const unique_keys = new Set();
            // Iterate files and create media src url for them
            for (let i = 0; i < filesArr.length; i++) {
                const file = filesArr[i];
                const meta = metadataArr[i];
                let mediaSrc;
                if (toSrc === null) {
                    mediaSrc = mediaUtils.createMediaSourceURL(meta.mimetype, mediaUtils.conversionUtils.binaryToBase64(file));
                } else {
                    mediaSrc = toSrc(file);
                }
                unique_keys.add(meta.key);
                // Push new object representing media with
                // the media url and the step
                console.log(mediaType);
                mediaReport.addDataOfType(
                    meta.key,
                    [{
                        wall_time: meta.wall_time,
                        value: mediaSrc,
                        step: meta.step
                    }],
                    meta,
                    mediaType
                );
            }
            // // Sort the datapoints for all image keys
            // for (const ukey of unique_keys) {
            //     mediaReport.media[mediaType][ukey].sort((a, b) => { return a.step - b.step; })
            // }
        }


        const generateStatReportFromZip = function(blob) {
            // Create zip object
            const zip = new JSZip();
            const indexFilename = "index.json";
            // Load zip data
            const loader = zip.loadAsync(blob).then((zip_contents) => {
                // Return promise processing contents...
                return zip.file(indexFilename).async("string").then((index_contents) => {
                    const index = JSON.parse(index_contents);
                    console.log("loaded index contents");
                    console.log(index);
                    // Setup report
                    // const mediaReport = {
                    //     simID: simulationID,
                    //     media: {
                    //         "scalars": {},
                    //         "images": {},
                    //         "audio": {},
                    //     }
                    // }
                    const report = new DataReport(index.sim_id);
                    
                    // Don't need to iterate the zip contents
                    // We just iterate through the index file instead
                    const streamer = index.streamer_key;
                    const fileMetadata_scalars = [];
                    const fileMetadata_images = [];
                    const fileMetadata_audio = [];
                    const filePromises_scalars = [];
                    const filePromises_images = [];
                    const filePromises_audio = [];
                    // Gather all promises and metadata for each info type
                    for (const filename in index.metadata["scalars"]) {
                        console.log(index.metadata["scalars"][filename]);
                        fileMetadata_scalars.push(index.metadata["scalars"][filename]);
                        filePromises_scalars.push(zip.file(filename).async("string"));
                    }
                    for (const filename in index.metadata["images"]) {
                        console.log(index.metadata["images"][filename]);
                        fileMetadata_images.push(index.metadata["images"][filename]);
                        filePromises_images.push(zip.file(filename).async("arraybuffer"));
                    }
                    for (const filename in index.metadata["audio"]) {
                        console.log(index.metadata["audio"][filename]);
                        fileMetadata_audio.push(index.metadata["audio"][filename]);
                        filePromises_audio.push(zip.file(filename).async("arraybuffer"));
                    }
                    // // Pre-make arrays for media types so when we process each file
                    // // we can use an existing array
                    // for (const meta of fileMetadata_images) {
                    //     console.log(meta);
                    //     if (!Object.hasOwn(mediaReport.media["images"], meta.key)) {
                    //         mediaReport.media["images"][meta.key] = [];
                    //     }
                    // }
                    // for (const meta of fileMetadata_audio) {
                    //     console.log(meta);
                    //     if (!Object.hasOwn(mediaReport.media["audio"], meta.key)) {
                    //         mediaReport.media["audio"][meta.key] = [];
                    //     }
                    // }
                    // Just place the scalar data into the proper scalar key
                    const scalarPromise = Promise.all(filePromises_scalars)
                        .then((files) => {
                            for (let i = 0; i < files.length; i++) {
                                // info should be an array of values (with steps)
                                const info = JSON.parse(files[i]);
                                const meta = fileMetadata_scalars[i];
                                report.addScalarData(meta.key, info, meta);
                                // mediaReport.media["scalars"][meta.key] = info;
                                // // Sort the datapoints for this key
                                // mediaReport.media["scalars"][meta.key].sort((a, b) => { return a.step - b.step; })
                            }
                        })
                        .catch((error) => {console.error(`Error processing scalars: ${error}`)});
                    // Process each image file and place the processed url
                    // and information into the image key array
                    const imagePromise = Promise.all(filePromises_images)
                        .then((files) => {
                            processMediaFilesToReport(report, "images", files, fileMetadata_images);
                        })
                        .catch((error) => {console.error(`Error processing images: ${error}`)});
                    // Process each audio file and place the processed url
                    // and information into the image key array
                    const audioPromise = Promise.all(filePromises_audio)
                        .then((files) => {
                            processMediaFilesToReport(report, "audio", files, fileMetadata_audio);
                        })
                        .catch((error) => {console.error(`Error processing audio: ${error}`)});
                    // Once all those promises are resolved, return the mediaReport promise
                    return Promise.all([scalarPromise, imagePromise, audioPromise])
                        .then((resolved) => {
                            // return Promise.resolve(mediaReport);
                            return Promise.resolve(report);
                        })
                        .catch((error) => {console.error(`Error processing media report resolution: ${error}`)})
                });
            });
            // Return promise of mediaReport
            return loader;
        }
        const getRecent = function(simID, tags=[], keys=[], exclusion_mode=false) {
            return fetchRecentForSimulation(simID, tags, keys, exclusion_mode)
                .then((response) => {
                    // The backend already sent a zip blob,
                    // we just need to interpret it as a zip.
                    console.log("Done fetching all recent simulation data");
                    const blob = response.blob();
                    // Return promise of media report
                    return generateStatReportFromZip(blob);
                })
                .catch((error) => {
                    console.error(`Problem calling getRecent on '${simID}': ${error}`)
                })
        }
        const getAll = function(simID, tags=[], keys=[], exclusion_mode=false) {
            return fetchAllForSimulation(simID, tags, keys, exclusion_mode)
                .then((response) => {
                    // The backend already sent a zip blob,
                    // we just need to interpret it as a zip.
                    console.log("Done fetching ALL simulation data");
                    const blob = response.blob();
                    // Return promise of media report
                    return generateStatReportFromZip(blob);
                })
                .catch((error) => {
                    console.error(`Problem calling getAll on '${simID}': ${error}`)
                })
        }

        // const dataReportUnion_CombineType = function(dr1, dr2, dataType) {
        //     for (const statKey in dr2.media[dataType]) {
        //         if (!Object.hasOwn(dr1.media[dataType], statKey)) {
        //             dr1.media[dataType][statKey] = [];
        //         }
        //         // Insert the new data in sorted order
        //         const d1 = dr1.media[dataType][statKey];
        //         const d2 = dr2.media[dataType][statKey];
        //         // Some basic checks before getting into the weeds.
        //         // If either is empty, then we just insert one into
        //         // the other.
        //         if (d1.length < 1 || d2.length < 1) {
        //             d1.push(...d2);
        //             continue;
        //         }
        //         // The typical use case means that the first value of
        //         // dr2 is USUALLY greater than the greatest/last value
        //         // of dr1, so we can just push all values right to the end.
        //         if (d1[d1.length-1].step < d2[0].step) {
        //             d1.push(...d2);
        //             continue;
        //         }
        //         // Iterate all the datapoints of 2nd report's keys
        //         let dr1_idx = 0;
        //         let dr2_idx = 0;
        //         while (dr2_idx < d2.length) {
        //             // If we are out of bounds of dr1, then
        //             // we know to just start inserting at the end.
        //             if (dr1_idx >= d1.length) {
        //                 d1.push(d2[dr2_idx]);
        //                 dr2_idx += 1;
        //                 continue;
        //             }
        //             // If current insert value is less than the current
        //             // value at dr1
        //             if (d2[dr2_idx].step < d1[dr1_idx].step) {
        //                 d1.splice(dr1_idx, 0, d2[dr2_idx]);
        //                 // Must push idx forward by 1 to keep place
        //                 dr1_idx += 1;
        //                 dr2_idx += 1;
        //             }
        //             // If current insert value is EQUAL, then
        //             // we REPLACE the value at dr1
        //             else if (d2[dr2_idx].step === d1[dr1_idx].step) {
        //                 d1[dr1_idx] = d2[dr2_idx];
        //                 dr2_idx += 1;
        //             }
        //             else {
        //                 dr1_idx += 1;
        //             }
        //         }
        //     }
        //     return dr1;
        // }
        // /**
        //  * Adds the contents of one data (dr2) report to another (dr1)
        //  * returning the first (dr1), modified data report. The data
        //  * reports must have the same simID. The data in both reports
        //  * should be already be sorted to accelerate combining.
        //  * 
        //  * @param {dataReport} dr1 
        //  * @param {dataReport} dr2 
        //  */
        // const dataReportUnion = function(dr1, dr2) {
        //     if (dr1.simID !== dr2.simID) {
        //         console.error(`Cannot combine data reports with different simID (${dr1.simID}, ${dr2.simID})`);
        //         return dr1;
        //     }
        //     dr1 = dataReportUnion_CombineType(dr1, dr2, "scalars");
        //     dr1 = dataReportUnion_CombineType(dr1, dr2, "images");
        //     dr1 = dataReportUnion_CombineType(dr1, dr2, "audio");
        //     return dr1;
        // }

        return {
            getAllNewScalars,
            getAllNewImages,
            getSimNewMedia,
            getRecent,
            getAll,
            createEmptyDataReport,
            DataReport,
            // dataReportUnion,
        };
    }
)();

export { dataUtils };