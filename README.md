<!--
SPDX-FileCopyrightText: 2024 PeARS Project, <community@pearsproject.org> 

SPDX-License-Identifier: AGPL-3.0-only
-->

# PeARS Lite - OMD integration


## What and why

**What:** *PeARS-OMD* is a version of PeARS used in the context of the project *On My Disk: search integration*. A description of the project can be found [on this page](https://www.ngisearch.eu/view/Events/FirstTenSearchersAnnounced). We are grateful to the Next Generation Internet programme of the European Commission for the financial support given to this project (see credits at the bottom of this README).

**Why:** This PeARS version is tailored for use with the [On My Disk](https://onmydisk.com/) private cloud solution. It includes features for indexing and search over a user's decentralised filesystem.




## Installation and Setup


##### 1. Clone this repo on your machine:

```
    git clone https://github.com/PeARSearch/PeARS-OMD.git
```

##### 2. **Optional step** Setup a virtualenv in your directory.

If you haven't yet set up virtualenv on your machine, please install it via pip:

    sudo apt update

    sudo apt install python3-setuptools

    sudo apt install python3-pip

    sudo apt install python3-virtualenv

Then change into the PeARS-OMD directory:

    cd PeARS-OMD

Then run:

    virtualenv env && source env/bin/activate


##### 3. Install the build dependencies:

From the PeARS-lite directory, run:

    pip install -r requirements.txt


##### 4. Set your authentification token

The PeARS authentification token is set in the *app/static/conf/pears.ini* file. Just replace *&lt;your auth token&gt;* with the string of your choice.


##### 5. Run your pear!

If you are running/testing PeARS-OMD locally (as opposed to the OMD server), first export the LOCAL_RUN variable and run the toy authentification server provided in *test-auth.py*:

```
export LOCAL_RUN=True
python3 test-auth.py  & python3 run.py 
```

If you are the OMD admin, run:

```
export LOCAL_RUN=False
python3 run.py
```

You should now see the login page of PeARS at http://localhost:9090/. You can sign in, either with your On My Disk credentials on the server, or if you are running locally, with a test user (username: tester, password: pwd).


NB: whenever you want to come back to a clean install, manually delete your database and pods:

```
rm -f app/static/db/app.db
rm -fr app/static/pods/*
```


## API Usage

To provide a toy example, the installation contains sample documents in the static folder, organised in folders as follows:

```
http://localhost:9090/static/testdocs/
    |_index.html
    |_tester/
        |_index.html
        |_localhost.localdomain
            |_index.html
            |_Downloads
                |_index.html
                |_sample2.txt
                |_sample3.txt
                |_sample4.txt
            |_Music
                |_index.html
            |_Pictures
                |_index.html
            |_Videos
                |_index.html
    |_shared/
        |_index.html
        |_shared_sample2.txt
        |_shared_sample3.txt
        |_shared_sample4.txt
```
			

NB: on the OMD server, the index.html files will be created on-the-fly at runtime.
 

To recursively crawl from base url:

```
curl localhost:9090/indexer/from_crawl?url=http://localhost:9090/static/testdocs/tester/index.html
curl localhost:9090/indexer/from_crawl?url=http://localhost:9090/static/testdocs/shared/index.html
```

The commands above will index the files of user *tester*, as well as public shares. A user should be able to search their own files, as well as public shares. An anonymous user should only be able to search public files. There are two different checkpoints for search as a logged in user and an anonymous user, as the following example searches demonstrate.

### Searching in anonymous mode

You can either search directly from the PeARS interface, or use cURL:

```
curl localhost:9090/anonymous?q=theory+of+nothing
```

The search function returns json objects containing all information about the selected URLs in the database in JSON format. For instance, searching for the phrase 'theory of nothing' returns the following document:

```
{
  "http://localhost:9090/static/testdocs/shared/shared_sample3.txt": {
    "cc": "False", 
    "date_created": "2023-11-06 09:59:18", 
    "date_modified": "2023-11-06 09:59:18", 
    "description": "A theater play.", 
    "id": "10", 
    "pod": "home", 
    "snippet": "The Theory of Nothing, a play about science and existentialism.  ", 
    "title": "Theory of Nothing", 
    "url": "http://localhost:9090/static/testdocs/shared/shared_sample3.txt", 
    "vector": "10"
  }
}

```

### Searching as a logged in user

This is easier to test from the PeARS interface. Make sure you are logged in (username: tester, password: pwd). You should now note that searching for 'theory' returns not only the shared document that we obtained in anonymous mode, but also another document stored under user *tester*:

```
{
  "http://localhost:9090/static/testdocs/shared/shared_sample3.txt": {
    "cc": "False", 
    "date_created": "2023-11-06 09:59:18", 
    "date_modified": "2023-11-06 09:59:18", 
    "description": "A theater play.", 
    "id": "10", 
    "pod": "home", 
    "snippet": "The Theory of Nothing, a play about science and existentialism.  ", 
    "title": "Theory of Nothing", 
    "url": "http://localhost:9090/static/testdocs/shared/shared_sample3.txt", 
    "vector": "10"
  }, 
  "http://localhost:9090/static/testdocs/tester/localhost.localdomain/Downloads/sample3.txt": {
    "cc": "False", 
    "date_created": "2023-11-06 09:59:10", 
    "date_modified": "2023-11-06 09:59:10", 
    "description": "The 347th draft of my theory of everything.", 
    "id": "7", 
    "pod": "home", 
    "snippet": "This is a theory of everything. It may not work as intended, but then theories of everything never do.  ", 
    "title": "Theory of Everything", 
    "url": "http://localhost:9090/static/testdocs/tester/localhost.localdomain/Downloads/sample3.txt", 
    "vector": "7"
  }
}
```


### Moving and deleting files

When logged in, it is possible to move and delete files. Moving a file involves the *api/urls/move* endpoint, and should be given the arguments *src* and *target*, referring to the source and destination paths of the file to be moved.


```
curl http://localhost:9090/api/urls/move?src=http://localhost:9090/static/testdocs/tester/localhost.localdomain/Downloads/sample3.txt\&target=http://localhost:9090/static/testdocs/shared/shared_sample5.txt
```

Deleting a file uses the *api/urls/delete* endpoint and takes a *path* argument referring to the path of the file to be deleted.

```
curl http://localhost:9090/api/urls/delete?path=http://localhost:9090/static/testdocs/tester/localhost.localdomain/Downloads/sample4.txt
```


## Adding your own data

To test PeARS-lite with your own data, you will have to set up a new user in the static/testdocs folder. The following illustrates this process with a toy example, to be run from the base directory.

First, we will assume that we have a folder somewhere on our computer, containing .txt files. For the sake of illustration, we will reuse the *static/testdocs/tester/localhost.localdomain/Downloads/* directory in this example, but you can use your own.

Second, we will create a new user with a *Documents* directory, where we will copy the .txt files from our chosen folder. There is a script in the root of the repo to do exactly this. You can feed it a new username and the path to the folder with your .txt documents. This script also sets up the directory structure required to match the OMD server. So for instance, let us create a new user called *myuser*, and copy some sample files to their space, using the content of our previous *Downloads* directory:

```
python3 mkuser.py myuser app/static/testdocs/tester/localhost.localdomain/Downloads/
```

The result of this call is a new *app/static/testdocs/myuser/* directory, with some .txt files in the *localhost.localdomain/Documents/* folder of that user.

Once we have done this, we can index the files of this new user: 

```
curl localhost:9090/indexer/from_crawl?url=http://localhost:9090/static/testdocs/myuser/index.html
```

And finally we can search as before:

```
curl localhost:9090?q=grandma
```

NB: again, if you would like to start from a clean install, do not forget to manually delete the existing index:

```
rm -f app/static/db/app.db
rm -fr app/static/pods/*npz
```

## Credits


<img src="https://pearsproject.org/images/NGI.png" width='400px'/>

Funded by the European Union. Views and opinions expressed are however those of the author(s) only and do not necessarily reflect those of the European Union or European Commission. Neither the European Union nor the granting authority can be held responsible for them. Funded within the framework of the NGI Search project under grant agreement No101069364.
