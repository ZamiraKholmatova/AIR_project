# Working with Google Drive

This is a simple web application, that finds duplicates and makes a search by a content among YOUR (means, that owner is you) 
text files from your Google Drive. You can also delete files, that application found. Libraries used in the project you can
see in [requirements.txt](https://github.com/ZamiraKholmatova/AIR_project/blob/master/requirements.txt)

## How to run this code?

You need to install [docker](https://docs.docker.com/get-docker/).
After it you can just run in your terminal 
```
docker run --rm -it -p 8080:8080 zamirakholmatova/air_project
```
And then go to [http://127.0.0.1:8080](http://127.0.0.1:8080)

Otherwise, you can build an image from Dockerfile:
```
 docker build air_project .
```
And then simply run:
```
docker run --rm -it -p 8080:8080 air_project
```

## How to use this application?

When you open this application the first time, you need to authorize. After authorization, you will see the button "Load files".
This button suggests you another three options: "Load files for fingind duplicates" (load files, find duplicates), 
"Loading files for search" (load files, build index - it is, unfortunately, spend much time), "Load both" (load files,
find duplicates, build index). These options download text files from a Google Drive. After building index or/and 
finding duplicates, these files will be deleted. 

To see the duplicates, chose "Find duplicates". Groups of similar files will be separated by the following
symbol: <li> </li>
"Search" button will open search form. Type your query, press "Search" and see the results.

The list of duplicates, list of text files on a Drive, built index are stored in a different files locally. 
So, if you will remove files or add new ones, you need to re-build your index and find your duplicates again. A button 
"Delete indices" will delete files, that store you index and list of duplicates. After removing, you can see button
"Load files" again!

After using this application, I will recommend you "Clear credentials", that will help you to obtain fresh data about what is
going on your Google Drive.
