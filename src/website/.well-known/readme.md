This folder contains the definition of the chatgpt plugin!

The assumption of these plugin is that there is a "API" (restful or just plain HTTP based) but that it has a openapi.yml definition which is API documentation standard. This would typically just declare a endpoint metadata like /speakerData?speakerName=XXXX 

I have added a folder called /api with an example of what the speakerData python code might look like and an example openapi.yml for that endpoint