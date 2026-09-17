pipeline {
    agent any

    stages {

        stage('Checkout') {
            steps {
                git branch: 'main',
                    credentialsId: 'github-argocd-cicd',
                    url: 'https://github.com/ParagGautam001/argocd-cicd-demo.git'
            }
        }

        stage('Verify') {
            steps {
                sh '''
                    echo "===== Jenkins CI ====="
                    echo "Git commit:"
                    git log -1 --oneline

                    echo ""
                    echo "Docker:"
                    docker --version

                    echo ""
                    echo "AWS:"
                    aws sts get-caller-identity

                    echo ""
                    echo "Project:"
                    ls -la
                '''
            }
        }
    }
}