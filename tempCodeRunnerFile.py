mode='dev'
if __name__ == '__main__':
    if mode=='dev':
         app.run(host='0.0.0.0', port=5000,debug=True)
    else:
     serve(app, host='0.0.0.0', port=5000, threads=2, url_prefix="/cec")