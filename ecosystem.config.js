module.exports = {
  apps: [{
    name: 'elo-api',
    script: 'venv/bin/gunicorn',
    args: '--bind 0.0.0.0:8000 app.wsgi:application',
    instances: 2,
    exec_mode: 'cluster',
    watch: false,
    env: {
      DJANGO_SETTINGS_MODULE: 'app.settings'
    },
    error_file: '/home/ec2-user/elo-api/logs/err.log',
    out_file: '/home/ec2-user/elo-api/logs/out.log',
    log_file: '/home/ec2-user/elo-api/logs/combined.log',
    time: true
  }]
}