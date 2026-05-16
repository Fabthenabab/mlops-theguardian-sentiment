// ============================================================
//  Jenkinsfile — mlops-theguardian-sentiment
//
//  Objectif : valider le code avant push GitHub.
//  Le déploiement HuggingFace (make + rsync) reste manuel.
//
//  Stages :
//    1. Checkout        — récupère le code
//    2. Install         — installe les dépendances dans le venv
//    3. Lint            — flake8 sur les modules critiques
//    4. Tests critical  — gate bloquant (pytest -m critical)
//    5. Tests smoke     — complément rapide (pytest -m smoke)
//
//  Notifications : Discord webhook en post (success / failure / always)
// ============================================================

def sendDiscord(String status, String color) {
    def emoji  = status == 'SUCCESS' ? '✅' : '❌'
    def label  = status == 'SUCCESS' ? 'RÉUSSI' : 'ÉCHOUÉ'
    sh """
        curl -s -X POST \\
            -H 'Content-Type: application/json' \\
            -d '{
                "embeds": [{
                    "title": "${emoji} BUILD ${label} — ${env.JOB_NAME} #${env.BUILD_NUMBER}",
                    "color": ${color},
                    "fields": [
                        {"name": "Branch",  "value": "${env.GIT_BRANCH}", "inline": true},
                        {"name": "Durée",   "value": "${currentBuild.durationString}", "inline": true},
                        {"name": "Détails", "value": "[Ouvrir Blue Ocean](${env.BUILD_URL})", "inline": false}
                    ]
                }]
            }' \\
            https://discord.com/api/webhooks/1502309018012614726/xfDkPI6fNHxA8ykoYRyEsw1QQd_eGAsR6tuKFl7r0z3YaZZVUfcXeFmVCzMJmgEPAXrU
    """
}


pipeline {
    agent any

    environment {
        VENV_DIR  = '.venv-jenkins'
        PYTHONPATH = "${env.WORKSPACE}"
        PROJECT_NAME = 'theguardian'
    }

    options {
        // Annule le build si pas de fin après 20 min
        timeout(time: 20, unit: 'MINUTES')
        // Garde les 10 derniers builds
        buildDiscarder(logRotator(numToKeepStr: '10'))
        // Pas de checkout automatique (on le fait dans le stage)
        skipDefaultCheckout()
    }

    stages {

        // ────────────────────────────────────────
        stage('Checkout') {
        // ────────────────────────────────────────
            steps {
                checkout scm
                echo "✓ Checkout — branch: 'main'"
            }
        }

        // ────────────────────────────────────────
        stage('Install') {
        // ────────────────────────────────────────
            steps {
                sh """
                    python3 -m venv ${VENV_DIR}
                    ${VENV_DIR}/bin/pip install --upgrade pip --quiet
                    ${VENV_DIR}/bin/pip install -r requirements-jenkins.txt --quiet
                """
                echo "✓ Dépendances installées"
            }
        }

        // ────────────────────────────────────────
        //stage('Lint') {
        // ────────────────────────────────────────
        //    steps {
        //        sh """
        //            ${VENV_DIR}/bin/flake8 \\
        //                pipeline/core/src/ \\
        //                _workers/ \\
        //                _server-fastapi/src/ \\
        //                --max-line-length=120 \\
        //                --exclude=__pycache__,.venv-jenkins \\
        //                --count \\
        //                --statistics
        //        """
        //      echo "✓ Lint OK"
        //    }
        //}

        // ────────────────────────────────────────
        stage('Tests — critical') {
        // ────────────────────────────────────────
        // Gate bloquant : 0 failure toléré.
        // Si ce stage échoue, le pipeline s'arrête ici.
        // ────────────────────────────────────────
            steps {
                sh """
                    ${VENV_DIR}/bin/pytest -m critical \\
                        --tb=short \\
                        --no-header \\
                        -q \\
                        --junit-xml=reports/critical.xml
                """
            }
            post {
                always {
                    junit 'reports/critical.xml'
                }
            }
        }

        // ────────────────────────────────────────
        stage('Tests — smoke') {
        // ────────────────────────────────────────
        // Non bloquant : un échec ici passe le build en UNSTABLE
        // mais ne bloque pas. On veut savoir, pas bloquer.
        // ────────────────────────────────────────
            steps {
                catchError(buildResult: 'UNSTABLE', stageResult: 'UNSTABLE') {
                    sh """
                        ${VENV_DIR}/bin/pytest -m smoke \\
                            --tb=short \\
                            --no-header \\
                            -q \\
                            --junit-xml=reports/smoke.xml
                    """
                }
            }
            post {
                always {
                    junit 'reports/smoke.xml'
                }
            }
        }
    }

    // ────────────────────────────────────────
    post {
    // ────────────────────────────────────────
        always {
            echo "Build terminé — statut : ${currentBuild.currentResult}"
            // Nettoyage venv pour ne pas polluer le workspace Jenkins
            sh "rm -rf ${VENV_DIR}"
        }
        success {
            sendDiscord('SUCCESS', '3066993')   // vert Discord
        }
        failure {
            sendDiscord('FAILURE', '15158332')  // rouge Discord
        }
        unstable {
            // Smoke failed mais critical OK — on notifie en orange
            sh """
                curl -s -X POST \\
                    -H 'Content-Type: application/json' \\
                    -d '{
                        "embeds": [{
                            "title": "⚠️ BUILD INSTABLE — ${env.JOB_NAME} #${env.BUILD_NUMBER}",
                            "color": 16776960,
                            "fields": [
                                {"name": "Cause",   "value": "Tests smoke en échec (critical OK)", "inline": false},
                                {"name": "Détails", "value": "[Ouvrir Blue Ocean](${env.BUILD_URL})", "inline": false}
                            ]
                        }]
                    }' \\
                    https://discord.com/api/webhooks/1502309018012614726/xfDkPI6fNHxA8ykoYRyEsw1QQd_eGAsR6tuKFl7r0z3YaZZVUfcXeFmVCzMJmgEPAXrU
            """
        }
    }
}