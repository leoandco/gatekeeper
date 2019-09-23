FROM python:3.7.4

RUN pip install pipenv

WORKDIR /src

COPY Pipfile Pipfile.lock ./
RUN pipenv install

COPY . .

ENTRYPOINT ["pipenv", "shell"]
CMD ["waitress-serve --call gatekeeper:create_app"]
