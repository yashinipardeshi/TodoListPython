pipeline {
    agent {
        label 'newNode'   // replace with your actual node label
    }

    environment {
        ARM_CLIENT_ID       = credentials('ARM_CLIENT_ID')
        ARM_CLIENT_SECRET   = credentials('ARM_CLIENT_SECRET')
        ARM_TENANT_ID       = credentials('ARM_TENANT_ID')
        ARM_SUBSCRIPTION_ID = credentials('ARM_SUBSCRIPTION_ID')
        DOCKER_USERNAME     = credentials('DOCKER_USERNAME')
        DOCKER_PAT          = credentials('DOCKER_PAT')

        IMAGE_NAME          = "${DOCKER_USERNAME}/todolist"
        IMAGE_TAG           = "${BUILD_NUMBER}"

        RESOURCE_GROUP      = "azure-terraform-git"
        LOCATION            = "eastus"
        ACA_ENV_NAME        = "todolist-env"
        ACA_APP_NAME        = "todolist-app2"
    }

    options {
        buildDiscarder(logRotator(numToKeepStr: '10'))
        timestamps()
        timeout(time: 30, unit: 'MINUTES')
        disableConcurrentBuilds(abortPrevious: false)
    }

    triggers {
        githubPush()
    }

    stages {

        stage('Verify Tools') {
            steps {
                // Sanity check — confirms az and docker are reachable on the slave
                sh '''
                    echo "--- Node info ---"
                    hostname
                    whoami
                    echo "--- Azure CLI ---"
                    az --version
                    echo "--- Docker ---"
                    docker --version
                '''
            }
        }

        stage('Checkout') {
            steps {
                git branch: 'master',
                    url: 'https://github.com/yashinipardeshi/TodoListPython/'
                echo "Cloned repo — commit: ${env.GIT_COMMIT?.take(7)}"
            }
        }

        stage('Build Docker Image') {
            steps {
                sh """
                    docker build \
                        -t ${IMAGE_NAME}:${IMAGE_TAG} \
                        -t ${IMAGE_NAME}:latest \
                        --label git-commit=${GIT_COMMIT} \
                        --label build-number=${BUILD_NUMBER} \
                        .
                """
                echo "Built: ${IMAGE_NAME}:${IMAGE_TAG}"
            }
        }

        stage('Push to Docker Hub') {
            steps {
                withCredentials([
                    string(credentialsId: 'DOCKER_USERNAME', variable: 'DOCKER_USER'),
                    string(credentialsId: 'DOCKER_PAT',      variable: 'DOCKER_TOKEN')
                ]) {
                    sh '''
                        echo "$DOCKER_TOKEN" | docker login -u "$DOCKER_USER" --password-stdin
                        docker push "$DOCKER_USER/todolist:$BUILD_NUMBER"
                        docker push "$DOCKER_USER/todolist:latest"
                        docker logout
                    '''
                }
                echo "Pushed ${IMAGE_NAME}:${IMAGE_TAG}"
            }
        }

        stage('Azure Login') {
            steps {
                withCredentials([
                    string(credentialsId: 'ARM_CLIENT_ID',       variable: 'AZ_CLIENT_ID'),
                    string(credentialsId: 'ARM_CLIENT_SECRET',   variable: 'AZ_CLIENT_SECRET'),
                    string(credentialsId: 'ARM_TENANT_ID',       variable: 'AZ_TENANT_ID'),
                    string(credentialsId: 'ARM_SUBSCRIPTION_ID', variable: 'AZ_SUB_ID')
                ]) {
                    sh '''
                        az login --service-principal \
                            -u "$AZ_CLIENT_ID" \
                            -p "$AZ_CLIENT_SECRET" \
                            --tenant "$AZ_TENANT_ID"
                        az account set --subscription "$AZ_SUB_ID"
                        az extension add --name containerapp --upgrade --yes 2>/dev/null || true
                        echo "Azure login successful"
                    '''
                }
            }
        }

        stage('Preview Deployment') {
            steps {
                script {
                    def appExists = sh(
                        script: '''
                            az containerapp show \
                                --name "$ACA_APP_NAME" \
                                --resource-group "$RESOURCE_GROUP" \
                                --query name -o tsv 2>/dev/null || echo ""
                        ''',
                        returnStdout: true
                    ).trim()

                    if (appExists) {
                        echo """
                        ========================================
                        DEPLOYMENT PREVIEW
                        ----------------------------------------
                        Action       : UPDATE existing app
                        App name     : ${ACA_APP_NAME}
                        Resource grp : ${RESOURCE_GROUP}
                        New image    : ${IMAGE_NAME}:${IMAGE_TAG}
                        Strategy     : Rolling revision (zero downtime)
                        ========================================
                        """
                        env.APP_EXISTS = "true"
                    } else {
                        echo """
                        ========================================
                        DEPLOYMENT PREVIEW
                        ----------------------------------------
                        Action       : CREATE new Container App
                        App name     : ${ACA_APP_NAME}
                        Environment  : ${ACA_ENV_NAME}
                        Resource grp : ${RESOURCE_GROUP}
                        Image        : ${IMAGE_NAME}:${IMAGE_TAG}
                        Port         : 8080 (external ingress)
                        Replicas     : min 1 / max 3
                        ========================================
                        """
                        env.APP_EXISTS = "false"
                    }
                }
            }
        }

        stage('Approval') {
            // Approval can run on master since it's just a UI pause
            agent { label 'built-in' }
            steps {
                input message: "Build #${BUILD_NUMBER} — Review deployment preview. Proceed?",
                      ok: 'Yes, Deploy!',
                      submitter: 'Yashini Pardeshi',
                      parameters: [
                          choice(
                              name: 'ACTION',
                              choices: ['Apply', 'Abort'],
                              description: 'Choose Apply to deploy or Abort to cancel'
                          )
                      ]
            }
        }

        stage('Provision ACA Environment') {
            steps {
                script {
                    def envExists = sh(
                        script: '''
                            az containerapp env show \
                                --name "$ACA_ENV_NAME" \
                                --resource-group "$RESOURCE_GROUP" \
                                --query name -o tsv 2>/dev/null || echo ""
                        ''',
                        returnStdout: true
                    ).trim()

                    if (envExists) {
                        echo "Environment '${ACA_ENV_NAME}' already exists — skipping"
                    } else {
                        echo "Creating Container Apps environment..."
                        sh '''
                            az containerapp env create \
                                --name "$ACA_ENV_NAME" \
                                --resource-group "$RESOURCE_GROUP" \
                                --location "$LOCATION" \
                                --output none
                        '''
                        echo "Environment created"
                    }
                }
            }
        }

        // stage('Deploy to Azure Container Apps') {
        //     steps {
        //         withCredentials([
        //             string(credentialsId: 'DOCKER_USERNAME', variable: 'DH_USER'),
        //             string(credentialsId: 'DOCKER_PAT',      variable: 'DH_TOKEN')
        //         ]) {
        //             script {
        //                 if (env.APP_EXISTS == "true") {
        //                     echo "Updating existing app to ${IMAGE_NAME}:${IMAGE_TAG}..."
        //                     sh """
        //                         az containerapp update \
        //                             --name "${ACA_APP_NAME}" \
        //                             --resource-group "${RESOURCE_GROUP}" \
        //                             --image "${IMAGE_NAME}:${IMAGE_TAG}" \
        //                             --output none
        //                     """
        //                 } else {
        //                     echo "Creating new Container App..."
        //                     sh '''
        //                         az containerapp create \
        //                             --name "$ACA_APP_NAME" \
        //                             --resource-group "$RESOURCE_GROUP" \
        //                             --environment "$ACA_ENV_NAME" \
        //                             --image "$DH_USER/todolist:$BUILD_NUMBER" \
        //                             --registry-server "index.docker.io" \
        //                             --registry-username "$DH_USER" \
        //                             --registry-password "$DH_TOKEN" \
        //                             --target-port 8080 \
        //                             --ingress external \
        //                             --min-replicas 1 \
        //                             --max-replicas 3 \
        //                             --cpu 0.5 \
        //                             --memory 1.0Gi \
        //                             --output none
        //                     '''
        //                 }

        //                 def appUrl = sh(
        //                     script: """
        //                         az containerapp show \
        //                             --name "${ACA_APP_NAME}" \
        //                             --resource-group "${RESOURCE_GROUP}" \
        //                             --query properties.configuration.ingress.fqdn \
        //                             --output tsv
        //                     """,
        //                     returnStdout: true
        //                 ).trim()

        //                 echo """
        //                 ========================================
        //                 DEPLOYMENT COMPLETE
        //                 Build    : #${BUILD_NUMBER}
        //                 Image    : ${IMAGE_NAME}:${IMAGE_TAG}
        //                 Live URL : https://${appUrl}
        //                 ========================================
        //                 """
        //                 env.APP_URL = appUrl
        //             }
        //         }
        //     }
        // }
        stage('Deploy to Azure Container Apps') {
        steps {
        withCredentials([
            string(credentialsId: 'DOCKER_USERNAME', variable: 'DH_USER'),
            string(credentialsId: 'DOCKER_PAT',      variable: 'DH_TOKEN')
        ]) {
            script {
                if (env.APP_EXISTS == "true") {
                    echo "Updating existing app — new revision will be created..."
                    sh """
                        /usr/bin/az containerapp update \
                            --name "${ACA_APP_NAME}" \
                            --resource-group "${RESOURCE_GROUP}" \
                            --image "${IMAGE_NAME}:${IMAGE_TAG}" \
                            --revision-suffix "build-${IMAGE_TAG}" \
                            --min-replicas 1 \
                            --max-replicas 3 \
                            --output none
                    """

                    // Show active revisions after update
                    sh """
                        echo "=== Active revisions ==="
                        /usr/bin/az containerapp revision list \
                            --name "${ACA_APP_NAME}" \
                            --resource-group "${RESOURCE_GROUP}" \
                            --query "[].{Name:name, Image:properties.template.containers[0].image, Active:properties.active, Traffic:properties.trafficWeight}" \
                            --output table
                    """

                } else {
                    echo "Creating new Container App with health probes..."
                    sh '''
                        /usr/bin/az containerapp create \
                            --name "$ACA_APP_NAME" \
                            --resource-group "$RESOURCE_GROUP" \
                            --environment "$ACA_ENV_NAME" \
                            --image "$DH_USER/todolist:$BUILD_NUMBER" \
                            --registry-server "index.docker.io" \
                            --registry-username "$DH_USER" \
                            --registry-password "$DH_TOKEN" \
                            --target-port 8080 \
                            --ingress external \
                            --min-replicas 1 \
                            --max-replicas 3 \
                            --cpu 0.5 \
                            --memory 1.0Gi \
                            --revision-suffix "build-$BUILD_NUMBER" \
                            --output none
                    '''
                }

                def appUrl = sh(
                    script: """
                        /usr/bin/az containerapp show \
                            --name "${ACA_APP_NAME}" \
                            --resource-group "${RESOURCE_GROUP}" \
                            --query properties.configuration.ingress.fqdn \
                            --output tsv
                    """,
                    returnStdout: true
                ).trim()

                echo """
                ========================================
                DEPLOYMENT COMPLETE
                Build    : #${BUILD_NUMBER}
                Image    : ${IMAGE_NAME}:${IMAGE_TAG}
                Revision : build-${IMAGE_TAG}
                Live URL : https://${appUrl}
                ========================================
                """
                env.APP_URL = appUrl
            }
        }
    }
}
    }

    post {
        success {
            echo "Build #${BUILD_NUMBER} succeeded — https://${env.APP_URL}"
        }
        failure {
            echo "Build #${BUILD_NUMBER} failed — check stage logs above"
        }
        aborted {
            echo "Build #${BUILD_NUMBER} aborted at Approval stage"
        }
        always {
            sh """
                docker rmi ${IMAGE_NAME}:${IMAGE_TAG} || true
                docker rmi ${IMAGE_NAME}:latest       || true
                az logout || true
            """
            echo "Cleaned up local images and Azure session"
        }
    }
}
