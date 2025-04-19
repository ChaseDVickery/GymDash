import { apiURL } from "./api_link.js";
import { mediaUtils } from "./media_utils.js";

const dataUtils = (
    function() {
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
        // const fetchAllRecentValues    = () => {return fetch(apiURL(`read-key/?exp_key=${encodeURIComponent("tb\\stock\\train")}&key=${encodeURIComponent("rollout/ep_rew_mean")}&recent=True`));}

        // Public Utilities
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
                                        url: mediaSrc,
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

        return {
            getAllNewScalars,
            getAllNewImages,
            getSimNewMedia
        };
    }
)();

export { dataUtils };