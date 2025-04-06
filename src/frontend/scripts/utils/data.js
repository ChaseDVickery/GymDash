import { apiURL } from "./api_link.js";
import { mediaUtils } from "./media_utils.js";

const dataUtils = (
    function() {
        const fetchAllRecentValues    = () => {return fetch(apiURL(`all-recent-scalars`));}
        const fetchAllRecentImages    = () => {return fetch(apiURL(`all-recent-images`), { responseType: 'blob' });}
        // const fetchAllRecentValues    = () => {return fetch(apiURL(`read-key/?exp_key=${encodeURIComponent("tb\\stock\\train")}&key=${encodeURIComponent("rollout/ep_rew_mean")}&recent=True`));}

        // Public Utilities
        const getAllNewScalars = function() {
            return fetchAllRecentValues()
                .then((response) => {
                    console.log(response);
                    return response.json();
                });
        }
        const getAllNewImages = function() {
            return fetchAllRecentImages()
                .then((response) => {
                    // The backend already sent a zip blob,
                    // we just need to interpret it as a zip.
                    const blob = response.blob();
                    // const buff = response.blob();
                    // console.log(buff);
                    // return buff;
                    const zip = new JSZip();
                    const indexFilename = "index.json";
                    const loader = zip.loadAsync(blob)
                        .then((zip_contents) => {
                            return zip.file(indexFilename).async("string").then((index_contents) => {
                                const index = JSON.parse(index_contents);
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
                                        const mediaSrcURLs = [];
                                        for (let i = 0; i < files.length; i++) {
                                            const file = files[i];
                                            const meta = fileMetadata[i];
                                            const mediaSrc = mediaUtils.createMediaSourceURL(meta.mimetype, mediaUtils.conversionUtils.binaryToBase64(file));
                                            mediaSrcURLs.push(mediaSrc);
                                        }
                                        return Promise.resolve(mediaSrcURLs);
                                    });
                                // Iterate zip files...
                                // Object.keys(contents.files).forEach((filename) => {
                                //     if (filename === indexFilename) { return; }
                                //     zip.file(filename)
                                // });
                            });
                        });
                    return loader;
                    // zip.file('downloaded_file', blob);
                    // return zip.generateAsync({ type: 'blob' });

                    // return blob;
                });
                // .then((zipBlob) => {
                //     const url = URL.createObjectURL(zipBlob);
                //     const link = document.createElement('a');
                //     link.href = url;
                //     link.download = 'download.zip';
                //     document.body.appendChild(link);
                //     link.click();
                //     document.body.removeChild(link);
                // })
        }

        return {
            getAllNewScalars,
            getAllNewImages
        };
    }
)();

export { dataUtils };