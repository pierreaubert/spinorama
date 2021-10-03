function downloadZip(url) {

    async function get(entry) {
        return entry.getData( new zip.TextWriter());
    };

    async function download(url)  {
        // console.log(`dowload start`);
        const cblob = new zip.HttpReader(url);
        const czip =  new zip.ZipReader(cblob);
        const entries = await czip.getEntries();
        if (entries && entries.length) {
            // console.log(`found ${entries.length} ${entries[0].filename}`);
            const text = await get(entries[0]);
            return text;
        }
        return "{}";
    };

    return download(url);
}
