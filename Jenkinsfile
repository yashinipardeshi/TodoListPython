pipeline {
    agent {
        label 'newNode'
    }

    environment {
        ARM_CLIENT_ID       = credentials('ARM_CLIENT_ID')
        ARM_CLIENT_SECRET   = credentials('ARM_CLIENT_SECRET')
        ARM_TENANT_ID       = credentials('ARM_TENANT_ID')
        ARM_SUBSCRIPTION_ID = credentials('ARM_SUBSCRIPTION_ID')

        ACR_NAME            = "yashiniregistry123"
        ACR_LOGIN_SERVER    = "yashiniregistry123.azurecr.io"
        IMAGE_NAME          = "yashiniregistry123.azurecr.io/todolist"
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

        stage('Push to ACR') {
            steps {
                sh '''
                    az acr login --name "$ACR_NAME"
                    docker push "${IMAGE_NAME}:${IMAGE_TAG}"
                    docker push "${IMAGE_NAME}:latest"
                    echo "Pushed ${IMAGE_NAME}:${IMAGE_TAG} to ACR"
                '''
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
                        Registry     : ${ACR_LOGIN_SERVER}
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
                        Registry     : ${ACR_LOGIN_SERVER}
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

        stage('Deploy to Azure Container Apps') {
            steps {
                script {
                    // Fetch ACR admin credentials
                    env.ACR_USERNAME = sh(
                        script: 'az acr credential show --name "$ACR_NAME" --query username -o tsv',
                        returnStdout: true
                    ).trim()
                    env.ACR_PASSWORD = sh(
                        script: 'az acr credential show --name "$ACR_NAME" --query "passwords[0].value" -o tsv',
                        returnStdout: true
                    ).trim()

                    if (env.APP_EXISTS == "true") {
                        echo "Registering ACR credentials on the app (idempotent)..."
                        sh """
                            /usr/bin/az containerapp registry set \
                                --name "${ACA_APP_NAME}" \
                                --resource-group "${RESOURCE_GROUP}" \
                                --server "${ACR_LOGIN_SERVER}" \
                                --username "${env.ACR_USERNAME}" \
                                --password "${env.ACR_PASSWORD}" \
                                --output none
                        """

                        echo "Updating image to ${IMAGE_NAME}:${IMAGE_TAG}..."
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

                        sh """
                            echo "=== Active revisions ==="
                            /usr/bin/az containerapp revision list \
                                --name "${ACA_APP_NAME}" \
                                --resource-group "${RESOURCE_GROUP}" \
                                --query "[].{Name:name, Image:properties.template.containers[0].image, Active:properties.active, Traffic:properties.trafficWeight}" \
                                --output table
                        """

                    } else {
                        echo "Creating new Container App pulling from ACR..."
                        sh """
                            /usr/bin/az containerapp create \
                                --name "${ACA_APP_NAME}" \
                                --resource-group "${RESOURCE_GROUP}" \
                                --environment "${ACA_ENV_NAME}" \
                                --image "${IMAGE_NAME}:${IMAGE_TAG}" \
                                --registry-server "${ACR_LOGIN_SERVER}" \
                                --registry-username "${env.ACR_USERNAME}" \
                                --registry-password "${env.ACR_PASSWORD}" \
                                --target-port 8080 \
                                --ingress external \
                                --min-replicas 1 \
                                --max-replicas 3 \
                                --cpu 0.5 \
                                --memory 1.0Gi \
                                --revision-suffix "build-${IMAGE_TAG}" \
                                --output none
                        """
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
                    Registry : ${ACR_LOGIN_SERVER}
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
