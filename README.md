# PWP SUMMER 2020

# ImageNet Browser

This project uses the example Flask API project layout, the introduction to which can be found here:  
https://lovelace.oulu.fi/ohjelmoitava-web/ohjelmoitava-web/flask-api-project-layout/

Namely, the MasonBuilder class and create_error_response function in imagenet_browser/utils.py as well as the submit_data function in client.py, are from the course material as is.

## Setup in development configuration

Download the Cygwin installer:  
https://cygwin.com/setup-x86_64.exe

Open a command prompt in the folder that you downloaded the Cygwin installer to and issue the following command:

```cmd
setup-x86_64 -OP git,python37,python37-pip,wget -qs https://ftp.acc.umu.se/mirror/cygwin/
```

Open a Cygwin terminal from the Start menu and issue the following commands:

```sh
git clone https://github.com/atheik/imagenet-browser.git
cd imagenet-browser
```

```sh
python3.7 -m venv venv
. venv/bin/activate
pip3.7 install -r requirements.txt
```

```sh
# instance/development.db is already populated and distributed in the repository
# the following ImageNet files are utilized for populating the initial database
wget http://www.image-net.org/archive/words.txt \
     http://www.image-net.org/archive/gloss.txt \
     http://www.image-net.org/archive/wordnet.is_a.txt \
     http://web.archive.org/web/20190130005544/http://image-net.org/imagenet_data/urls/imagenet_fall11_urls.tgz
```

```sh
# only the first 100000 images are used due to repository storage considerations
tar xf imagenet_fall11_urls.tgz
mv fall11_urls.txt{,.full}
head -100000 fall11_urls.txt.full > fall11_urls.txt
```

```sh
export FLASK_APP=imagenet_browser
export FLASK_ENV=development
flask init-db && flask load-db # remove instance/development.db first if you wish to run this command
flask run
```

The entry point is at:  
http://localhost:5000/api/

## Testing

Make sure your environment is setup as in the development configuration described above.  
The coverage reported for the database and resource tests should be 98%.

```sh
pytest --cov=imagenet_browser --cov-report=term-missing
```

## Client

Make sure your environment is setup as in the development configuration described above.  
Remember to run the server in another terminal.

```sh
python3.7 client.py
```

# Group information

* Student 1. Atte Heikkilä (Atte.Heikkila@student.oulu.fi)

__Remember to include all required documentation and HOWTOs, including how to create and populate the database, how to run and test the API, the url to the entrypoint and instructions on how to setup and run the client__
