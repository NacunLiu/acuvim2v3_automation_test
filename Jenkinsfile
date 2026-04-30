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

                echo "Handing USB serial adapter (COM6) from Windows to WSL via usbipd..."
                powershell '''
                    $attached = $false
                    $candidates = usbipd list | Select-String -Pattern "0403:6001"
                    foreach ($line in $candidates) {
                        $busid = ($line.ToString().Trim() -split " ")[0]
                        Write-Host "Trying bus ID $busid..."
                        usbipd bind --busid $busid --force 2>$null
                        usbipd attach --wsl --busid $busid 2>$null
                        Start-Sleep 2
                        $com6_gone = -not (Get-WmiObject Win32_SerialPort | Where-Object { $_.DeviceID -eq "COM6" })
                        if ($com6_gone) {
                            Write-Host "COM6 device successfully attached to WSL via bus ID $busid"
                            $attached = $true
                            break
                        }
                        Write-Host "Bus ID $busid was not COM6, detaching..."
                        usbipd detach --busid $busid 2>$null
                    }
                    if (-not $attached) {
                        Write-Host "WARNING: Could not identify and attach COM6 device to WSL"
                    }
                '''
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
                echo "Verifying USB serial adapter is visible in WSL..."
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
                        python3 \
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
