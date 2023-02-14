# !/bin/sh

# This runs the build phase of the build.
#
# To run outside codebuild,set the following variables before running:
# Template_Path
# Set this to the path to the template.yml file at the root of your project.
# s3_Deploy_Bucket
# Set this to the name of an S3 bucket you control.
#
# Be sure you are logged in to AWS, as this script uploads to S3.
build_application(){
    sam build --template-file ${TEMPLATE_PATH}
}

package_application(){
    ### YOU MUST SPECIFY A KMS TO USE WHEN PACKAGING YOUR TEMPLATE ###
    sam package --template-file .aws-sam/build/template.yml --kms-key-id alias/aws/s3 --
}

echo "Starting build - $(date)"
set -xe
build_application
package_applicatione
echo "Completed build - $(date)"