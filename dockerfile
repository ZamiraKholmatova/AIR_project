FROM python:3.6-slim

WORKDIR /app

COPY templates/ /app/templates

COPY air_project.py /app/

COPY external_methods.py /app/

COPY norvig_spellcheker.py /app/

COPY vocabulary /app/

COPY requirements.txt /app/

COPY client_id.json /app

RUN pip install -r requirements.txt

ENV gapp_secret  b'\x07L\xd6\xdfp\xca\xdd\x19\xa8,\xfc\x9a#\x04`|'

EXPOSE 8080/tcp

CMD [ "python","air_project.py" ] 
