import { apiURL } from "./api_link.js";

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
                    const blob = response.blob();
                    // const buff = response.blob();
                    // console.log(buff);
                    // return buff;
                    const zip = new JSZip();
                    zip.file('downloaded_file', blob);
                    return zip.generateAsync({ type: 'blob' });
                })
                .then((zipBlob) => {
                    const url = URL.createObjectURL(zipBlob);
                    const link = document.createElement('a');
                    link.href = url;
                    link.download = 'download.zip';
                    document.body.appendChild(link);
                    link.click();
                    document.body.removeChild(link);
                })
        }

        return {
            getAllNewScalars,
            getAllNewImages
        };
    }
)();

export { dataUtils };