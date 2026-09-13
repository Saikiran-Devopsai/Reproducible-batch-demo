// Jenkinsfile
//
// Builds the claims-batch-processor Docker image and runs it exactly
// the same way a developer would run it locally -- same image, same
// mounted input/output folders, same command. Jenkins isn't doing
// anything "special": it's running the identical docker build/run
// commands a human would type, just triggered automatically on every
// commit instead of by hand.

pipeline {
    agent any

    environment {
        IMAGE_NAME = "claims-batch-processor"
        IMAGE_TAG  = "${env.BUILD_NUMBER}"
    }

    options {
        timeout(time: 15, unit: 'MINUTES')
        timestamps()
    }

    stages {

        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Build Image') {
            steps {
                sh "docker build -t ${IMAGE_NAME}:${IMAGE_TAG} ."
            }
        }

        stage('Generate Test Data') {
            // Reproducibility check: same synthetic-data generator runs
            // here as it would on a developer's laptop -- guarantees
            // Jenkins is testing against the same scale/shape of input
            // every single build, not whatever happens to be lying
            // around on someone's machine.
            steps {
                sh 'python3 generate_sample_data.py --count 300 --rows-per-file 15 --output-dir input_ci'
            }
        }

        stage('Run Batch Job') {
            steps {
                sh 'mkdir -p output_ci'
                sh """
                    docker run --rm \
                        -v \$(pwd)/input_ci:/app/input \
                        -v \$(pwd)/output_ci:/app/output \
                        ${IMAGE_NAME}:${IMAGE_TAG}
                """
            }
        }

        stage('Verify Output') {
            // Fail the build loudly if the report wasn't produced --
            // this is the CI equivalent of "did the job actually work,"
            // not just "did the container start."
            steps {
                sh '''
                    if [ ! -f output_ci/summary_report.json ]; then
                        echo "ERROR: summary_report.json was not generated."
                        exit 1
                    fi
                    echo "Report generated successfully:"
                    cat output_ci/summary_report.txt
                '''
            }
        }
    }

    post {
        always {
            // Clean up CI-generated test data/output so it doesn't
            // pile up across builds -- keeps the workspace reproducible
            // for the NEXT run too, not just this one.
            sh 'rm -rf input_ci output_ci'
            archiveArtifacts artifacts: 'output_ci/**', allowEmptyArchive: true
        }
        failure {
            echo "Build failed -- check console output above for the failing stage."
        }
    }
}
