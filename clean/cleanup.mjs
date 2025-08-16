import S3 from 'aws-sdk/clients/s3.js';
let accountid = process.env.R2_ACCOUNT_ID;
let access_key_id = process.env.R2_ACCESS_ID;
let access_key_secret = process.env.R2_ACCESS_SECRET;
let bucket = process.env.R2_BUCKET_NAME || 'my-bucket'
if (!accountid || !access_key_id || !access_key_secret) {
    console.error("Required parameter not found");
    process.exit(1);
}
const s3 = new S3({
    endpoint: `https://${accountid}.r2.cloudflarestorage.com`,
    accessKeyId: `${access_key_id}`,
    secretAccessKey: `${access_key_secret}`,
    signatureVersion: 'v4',
});

// Remove Duplicate Contents
let contents = (await s3.listObjects({ Bucket: bucket }).promise())['Contents'];
let unqiue = new Map();
for (let content of contents) {
    if (unqiue.has(content.ETag)) {
        // Duplicate
        let params = {
            Bucket: bucket,
            Key: content.Key
        };
        (await s3.deleteObject(params).promise())
        console.log("Duplicate Content", content.Key);
        break;
    }
    unqiue.set(content.ETag, "");
}
// Remove Content Older than 3 Days.
const today = new Date();
const sevenDaysAgo = new Date(today.getTime() - (3 * 24 * 60 * 60 * 1000));
contents = (await s3.listObjects({ Bucket: bucket }).promise())['Contents'];
if(contents.length <= 7){
    console.log("Not Deleting anything");
}
if(contents.length > 7){
for (let content of contents) {
    if (new Date(content.LastModified) < sevenDaysAgo) {
        let params = {
            Bucket: bucket,
            Key: content.Key
        };
        (await s3.deleteObject(params).promise())
        console.log("7 day old Content Deleted", content.Key);
    }
}
}
