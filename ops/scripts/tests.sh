#!/bin/bash

python -m pytest --alluredir allure-results
allure generate allure-results --clean -o allure-report
