#!/bin/bash

g++ -DNDEBUG -std=c++17 -Wall -pedantic-errors -Werror -g -o mtm_blockchain *.cpp
python3 ./tests/run_tests.py ./tests