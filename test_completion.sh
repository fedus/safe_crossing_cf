#!/bin/bash

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Testing City Completion Implementation ===${NC}"

# Check if Flask server is running
if ! curl -s http://localhost:5001/health > /dev/null; then
    echo -e "${RED}Flask server is not running. Please start it first:${NC}"
    echo "python run.py"
    exit 1
fi

# Initialize the database
echo -e "\n${BLUE}Initializing test database...${NC}"
python init_test_db.py
INIT_RESULT=$?

if [ $INIT_RESULT -ne 0 ]; then
    echo -e "${RED}Failed to initialize test database.${NC}"
    exit 1
fi

# Run the manual test script
echo -e "\n${BLUE}Running manual test script...${NC}"
python test_city_completion.py
MANUAL_TEST_RESULT=$?

# Run the unit tests
echo -e "\n${BLUE}Running automated unit tests...${NC}"
python -m unittest tests/test_city_completion.py
UNIT_TEST_RESULT=$?

# Report results
echo -e "\n${BLUE}=== Test Results ===${NC}"

if [ $MANUAL_TEST_RESULT -eq 0 ]; then
    echo -e "${GREEN}✓ Manual tests passed${NC}"
else
    echo -e "${RED}✗ Manual tests failed${NC}"
fi

if [ $UNIT_TEST_RESULT -eq 0 ]; then
    echo -e "${GREEN}✓ Unit tests passed${NC}"
else
    echo -e "${RED}✗ Unit tests failed${NC}"
fi

# Overall status
if [ $MANUAL_TEST_RESULT -eq 0 ] && [ $UNIT_TEST_RESULT -eq 0 ]; then
    echo -e "\n${GREEN}All tests passed successfully!${NC}"
    exit 0
else
    echo -e "\n${RED}Some tests failed. Please check the output above for details.${NC}"
    exit 1
fi 