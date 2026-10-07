#!/bin/sh
# LOCAL EMULATOR ONLY. Runs the real AWS CLI (from the amazon/aws-cli image) against the
# moto server on localhost:5050, with the same dummy credentials as emulator_override.tf.
# Usage: ./aws-emu.sh ec2 describe-vpcs ...   (on real AWS, just use `aws ...`)
exec docker run --rm \
  -e AWS_ACCESS_KEY_ID=test -e AWS_SECRET_ACCESS_KEY=test -e AWS_DEFAULT_REGION=ap-south-1 \
  amazon/aws-cli --endpoint-url http://host.docker.internal:5050 "$@"
