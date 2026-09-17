pipeline {
    agent any

    environment {
        AWS_REGION  = 'us-east-1'

        BACKEND_ECR  = '472864302807.dkr.ecr.us-east-1.amazonaws.com/backend'
        FRONTEND_ECR = 'public.ecr.aws/m1e5l6p3/frontend'

        GITHUB_REPO = 'https://github.com/ParagGautam001/argocd-cicd-demo.git'
    }

    stages {

        stage('Checkout') {
            steps {
                git branch: 'main',
                    credentialsId: 'github-argocd-cicd',
                    url: "${GITHUB_REPO}"
            }
        }

        stage('Verify') {
            steps {
                sh '''
                    set -e

                    echo "===== Jenkins CI ====="
                    echo "Git commit:"
                    git log -1 --oneline

                    echo ""
                    echo "Docker:"
                    docker --version

                    echo ""
                    echo "AWS Identity:"
                    aws sts get-caller-identity

                    echo ""
                    echo "Project:"
                    ls -la
                '''
            }
        }

        stage('Set Image Tag') {
            steps {
                script {
                    env.IMAGE_TAG = sh(
                        script: "git rev-parse --short=7 HEAD",
                        returnStdout: true
                    ).trim()

                    echo "Image Tag: ${env.IMAGE_TAG}"
                }
            }
        }

        stage('Login to Private ECR') {
            steps {
                sh '''
                    set -e

                    echo "===== Login to Private ECR ====="

                    aws ecr get-login-password \
                        --region ${AWS_REGION} | \
                    docker login \
                        --username AWS \
                        --password-stdin ${BACKEND_ECR}
                '''
            }
        }

        stage('Login to Public ECR') {
            steps {
                sh '''
                    set -e

                    echo "===== Login to Public ECR ====="

                    aws ecr-public get-login-password \
                        --region us-east-1 | \
                    docker login \
                        --username AWS \
                        --password-stdin public.ecr.aws
                '''
            }
        }

        stage('Build Frontend Image') {
            steps {
                sh '''
                    set -e

                    echo "===== Build Frontend ====="

                    docker build \
                        -t ${FRONTEND_ECR}:${IMAGE_TAG} \
                        ./frontend
                '''
            }
        }

        stage('Push Frontend Image') {
            steps {
                sh '''
                    set -e

                    echo "===== Push Frontend ====="

                    docker push ${FRONTEND_ECR}:${IMAGE_TAG}
                '''
            }
        }

        stage('Build Backend Image') {
            steps {
                sh '''
                    set -e

                    echo "===== Build Backend ====="

                    docker build \
                        -t ${BACKEND_ECR}:${IMAGE_TAG} \
                        ./backend
                '''
            }
        }

        stage('Push Backend Image') {
            steps {
                sh '''
                    set -e

                    echo "===== Push Backend ====="

                    docker push ${BACKEND_ECR}:${IMAGE_TAG}
                '''
            }
        }

        stage('Update Kubernetes Manifests') {
            steps {
                sh '''
                    set -e

                    echo "===== Update Kubernetes Images ====="

                    sed -i \
                        "s|image: .*backend:.*|image: ${BACKEND_ECR}:${IMAGE_TAG}|g" \
                        k8s/backend-deployment.yaml

                    sed -i \
                        "s|image: .*frontend:.*|image: ${FRONTEND_ECR}:${IMAGE_TAG}|g" \
                        k8s/frontend-deployment.yaml

                    echo ""
                    echo "Backend image:"
                    grep "image:" k8s/backend-deployment.yaml

                    echo ""
                    echo "Frontend image:"
                    grep "image:" k8s/frontend-deployment.yaml
                '''
            }
        }

        stage('Validate Kubernetes Manifests') {
            steps {
                sh '''
                    set -e

                    echo "===== Validate Kustomize ====="

                    kubectl kustomize k8s > /tmp/kustomized.yaml

                    echo "Kustomize validation successful"
                '''
            }
        }

        stage('Commit and Push Manifests') {
            steps {
                withCredentials([
                    usernamePassword(
                        credentialsId: 'github-argocd-cicd',
                        usernameVariable: 'GIT_USERNAME',
                        passwordVariable: 'GIT_PASSWORD'
                    )
                ]) {
                    sh '''
                        set -e

                        echo "===== Commit Kubernetes Manifest Changes ====="

                        git config user.name "jenkins"
                        git config user.email "jenkins@local"

                        git add k8s/backend-deployment.yaml
                        git add k8s/frontend-deployment.yaml

                        if git diff --cached --quiet; then
                            echo "No manifest changes detected"
                            exit 0
                        fi

                        git commit -m "Update images to ${IMAGE_TAG}"

                        git push origin HEAD:main
                    '''
                }
            }
        }
    }

    post {
        success {
            echo '===== Jenkins CI SUCCESS ====='
        }

        failure {
            echo '===== Jenkins CI FAILED ====='
        }

        always {
            sh '''
                echo "===== Workspace Status ====="
                git status || true
            '''
        }
    }
}