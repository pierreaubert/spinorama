# Install 'deepsource CLI'
if [[! -x bin/deepsource]]; then
   curl https://deepsource.io/cli | sh
fi

# Set DEEPSOURCE_DSN env variable from repository settings page
export DEEPSOURCE_DSN=https://sampledsn@deepsource.io

# From the root directory, run the report coverage command
./bin/deepsource report --analyzer test-coverage --key python --value-file ./coverage.xml
