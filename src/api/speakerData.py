from fastapi import FastAPI

app = FastAPI()


# Define some example speaker data     
#  
#  Should be something like this as per your code 
# df = {}
#   speakers = glob("{}/*".format(cpaths.CPATH_DOCS_SPEAKERS))
#     for speaker in speakers:
#       if not os.path.isdir(speaker):
#           continue
#       # humm annoying
#       speaker_name = speaker.replace(cpaths.CPATH_DOCS_SPEAKERS + "/", "")

speakers = [
    {
        "name": "KEF LS50",
        "referenceToDatas": "/datas/XXX"
    },
    {
        "name": "KEF LS50 (Meta)",
        "referenceToDatas": "/datas/XXX"
    }
]

# Define a route for the /speakerData endpoint
@app.get("/speakerData")
async def get_speaker_data(speakerName: str = None):
    if speakerName:
        # If a speakerName is provided, find the speaker with that name
        for speaker in speakers:
            if speaker["name"] == speakerName:
                return speaker
        # If the speaker isn't found, return a 404 error
        return {"error": "Speaker not found"}
    else:
        # If no speakerName is provided, return a list of all speakers
        return speakers