const { app, BrowserWindow } = require('electron');
const { spawn } = require('child_process');

let flaskProcess;

function createWindow () {
  const win = new BrowserWindow({
    width: 800,
    height: 600,
    webPreferences: {
      nodeIntegration: false
    }
  });

  win.loadFile('index.html');
}

app.whenReady().then(() => {
  // Spustíme Flask server (předpoklad: python a app/main.py existují)
  flaskProcess = spawn('python', ['app/main.py'], {
    cwd: __dirname
  });

  flaskProcess.stdout.on('data', (data) => {
    console.log(`[Flask]: ${data}`);
  });

  flaskProcess.stderr.on('data', (data) => {
    console.error(`[Flask Error]: ${data}`);
  });

  flaskProcess.on('error', (err) => {
    console.error(`[Flask Failed]: ${err}`);
    app.quit();
  });

  flaskProcess.on('exit', (code, signal) => {
    if (code !== 0) {
      console.error(`[Flask Exited]: code ${code}${signal ? ` signal ${signal}` : ''}`);
    }
    app.quit();
  });

  createWindow();

  app.on('activate', function () {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', function () {
  if (flaskProcess) flaskProcess.kill();
  if (process.platform !== 'darwin') app.quit();
});
