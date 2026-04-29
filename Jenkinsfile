pipeline {
    agent none

    options {
        timeout(time: 3, unit: 'HOURS')
        timestamps()
        buildDiscarder(logRotator(numToKeepStr: '20'))
        disableConcurrentBuilds()
    }

    environment {
        REPORT_EMAIL = 'nacun.liu@accuenergy.com'
        TEST_DIR     = 'communication_protocol_test'
    }

    stages {

        // ─────────────────────────────────────────────────────────────
        // STAGE 1 — Firmware Update  (Windows agent)
        // ─────────────────────────────────────────────────────────────
        stage('Firmware Update') {
            agent { label 'windows' }

            environment {
                USPROGRAM_EXE_PATH = 'C:\\Users\\NacunLiu\\Nacun_Work\\test apps install package\\Acuvim-II v3 USProgram English\\Acuvim-II v3 USProgram English\\USProgram.exe'
                FIRMWARE_DIR       = 'C:\\Users\\NacunLiu\\Downloads'
                ACU_WIN_COM_PORT   = 'COM6'
            }

            steps {
                echo "Installing Windows Python dependencies..."
                bat 'pip install pywinauto --quiet --disable-pip-version-check'

                echo "Running firmware update via USProgram..."
                bat 'python launch_usprogram.py'

                echo "Waiting 90 s for meter to reboot after firmware flash..."
                sleep time: 90, unit: 'SECONDS'
            }

            post {
                success { echo 'Firmware update completed successfully.' }
                failure  { echo 'Firmware update FAILED — aborting pipeline.' }
            }
        }

        // ─────────────────────────────────────────────────────────────
        // STAGE 2 — Prepare WSL environment  (built-in / WSL node)
        // ─────────────────────────────────────────────────────────────
        stage('Prepare Environment') {
            agent { label 'built-in' }

            steps {
                echo "Attaching USB serial adapter from Windows to WSL via usbipd..."
                sh '''
                    BUSID=$(powershell.exe -Command \
                        "usbipd list" 2>/dev/null \
                        | grep -iE "CP210|CH340|FTDI|USB Serial|USB-SERIAL" \
                        | awk "{print \\$1}" | head -1 || true)
                    if [ -n "$BUSID" ]; then
                        echo "Attaching USB bus ID $BUSID to WSL..."
                        powershell.exe -Command "usbipd attach --wsl --busid $BUSID" || true
                        sleep 3
                    else
                        echo "usbipd not available or device not found — assuming /dev/ttyUSB0 is already attached."
                    fi
                '''

                echo "Verifying serial port is visible..."
                sh 'ls /dev/ttyUSB* || (echo "ERROR: No USB serial adapter found in WSL. See scripts/setup_wsl_env.sh." && exit 1)'

                echo "Setting up Python virtual environment..."
                sh '''
                    python3 -m venv "${WORKSPACE}/venv"
                    "${WORKSPACE}/venv/bin/pip" install --upgrade pip --quiet
                    "${WORKSPACE}/venv/bin/pip" install \
                        -r "${WORKSPACE}/${TEST_DIR}/requirements.txt" \
                        --quiet
                '''
            }
        }

        // ─────────────────────────────────────────────────────────────
        // STAGE 3 — Communication Protocol Tests  (built-in / WSL node)
        // ─────────────────────────────────────────────────────────────
        stage('Communication Protocol Tests') {
            agent { label 'built-in' }

            environment {
                // Kasa plug direct IP — bypasses nmap scan
                ACU_PLUG_2_IP    = '172.27.24.166'
                ACU_PLUG_ID      = '2'
                // Serial port for Modbus RTU
                ACU_PORT         = '/dev/ttyUSB0'
                // Non-interactive CI mode
                ACU_BATCH_MODE   = 'true'
                ACU_MANUAL_POWER = 'false'
                // Disable desktop automation (no display on CI)
                ACU_ENABLE_BROWSER      = 'false'
                ACU_ENABLE_UI_AUTOMATION = 'false'
            }

            steps {
                dir("${TEST_DIR}") {
                    sh '"${WORKSPACE}/venv/bin/python" run.py'
                }
            }

            post {
                always {
                    archiveArtifacts(
                        artifacts: "${TEST_DIR}/logs/*.log",
                        allowEmptyArchive: true,
                        fingerprint: true
                    )
                    archiveArtifacts(
                        artifacts: "${TEST_DIR}/data/*.png",
                        allowEmptyArchive: true
                    )
                }
            }
        }
    }

    // ─────────────────────────────────────────────────────────────────
    // POST — Email report regardless of pass/fail
    // ─────────────────────────────────────────────────────────────────
    post {
        always {
            node('built-in') {
                withCredentials([
                    usernamePassword(
                        credentialsId: 'Gmail',
                        usernameVariable: 'GMAIL_USER',
                        passwordVariable: 'GMAIL_PASS'
                    )
                ]) {
                    sh """
                        "${WORKSPACE}/venv/bin/python" \
                            "${WORKSPACE}/scripts/send_report.py" \
                            "${currentBuild.result ?: 'SUCCESS'}" \
                            "${env.BUILD_NUMBER}" \
                            "${env.BUILD_URL}" \
                            "${WORKSPACE}/${TEST_DIR}"
                    """
                }
            }
        }
    }
}
