# https://github.com/hharnisc/python-meteor
import time
from datetime import datetime
import base64
import sys
print(sys.version)
print(sys.executable)

from lib.meteor.MeteorClient import MeteorClient
import SessionManager
import ImageController


import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import io

client = MeteorClient('ws://127.0.0.1:3000/websocket')

####  grimmer's experiment
getSessionCmd = "getSessionId"
sefSessionID = None
command_REGISTER_IMAGEVIEWER = '/CartaObjects/ViewManager:registerView'
command_SELECT_FILE_TO_OPEN = '/CartaObjects/ViewManager:dataLoaded'
controllerID = None
numberOfImages = 0
GET_IMAGE = 'GET_IMAGE'
testimage = 0

# https://stackoverflow.com/a/39662359/7354486
def isnotebook():
    try:
        shell = get_ipython().__class__.__name__
        if shell == 'ZMQInteractiveShell':
            return True   # Jupyter notebook or qtconsole
        elif shell == 'TerminalInteractiveShell':
            return False  # Terminal running IPython
        else:
            return False  # Other type (?)
    except NameError:
        return False      # Probably standard Python interpreter

# https://stackoverflow.com/a/5377051/7354486
def run_from_ipython():
    try:
        __IPYTHON__
        return True
    except NameError:
        return False

def subscribed(subscription):
    print('* SUBSCRIBED {}'.format(subscription))

def unsubscribed(subscription):
    print('* UNSUBSCRIBED {}'.format(subscription))

def remove_callback(error, data):
    print("in remove_callback")
    if error:
        print(error)
        return
    print(data)

def remove_image_callback(error, data):
    print("in remove_image_callback")
    if error:
        print(error)
        return
    print("in remove_image_callback ok")
    # print(data)

def insert_callback(error, data):
    print("insert callback")
    if error:
        print(error)
        return
    print("insert callback ok")
    # docs = client.find(collection, selector={'sessionID': sessionID})

    # print(data)

def update_callback(error, data):
    print("update callback")
    if error:
        print(error)
        return
    print("udpate callback ok")
    # print(data)

# python client seems to have no Optimistic update on py-client https://www.meteor.com/tutorials/blaze/security-with-methods
def saveDataToCollection(collection, newDocObject, actionType):
    sessionID = SessionManager.getSuitableSession()
    docs = client.find(collection, selector={'sessionID': sessionID})
    total = len(docs)
    if total > 0:
        print("try to replace first image in mongo, total images:", total)
        doc = docs[0]
        docID = doc["_id"]
        newDocObject["sessionID"] = sessionID
        # update, not test yet
        client.update(collection, {'_id': docID}, newDocObject, callback=update_callback)
    else:
        # insert
        print("try to to insert images")
        newDocObject["sessionID"] = sessionID
        client.insert(collection, newDocObject, callback=insert_callback)
        print("end to insert")

        #     newDocObject.sessionID = sessionID;
        #const docID = collection.insert(newDocObject);

    # save to mongo , imagecontroller
    # mongoUpsert(ImageController, { imageURL: url }, GET_IMAGE);
    # const url = `data:image/jpeg;base64,${buffer}`;
    # console.log('image url string size:', url.length);
# fields are changed fields
def handleAddedOrChanged(collection, id, fields):
    for key, value in fields.items():
        print('  - FIELD {}'.format(key))
        # print('  - FIELD {} {}'.format(key, value))

    if collection == "users":
        print("grimmer users added/changed ")
    elif collection == "responses":
        print("grimmer responses added/changed, self_sessionID:", fields["sessionID"])

        cmd = fields["cmd"]

        #1. TODO handle it
        if cmd == command_REGISTER_IMAGEVIEWER:
            print("response:REGISTER_IMAGEVIEWER")
            data = fields["data"] # save controllerID to use
            # will send setSize inside
            ImageController.parseReigsterViewResp(client, data)

        elif cmd == command_SELECT_FILE_TO_OPEN:
            print("response:SELECT_FILE_TO_OPEN")
            if "buffer" in fields:
                print("get image !!!!")
                imgString = fields["buffer"]
                imageLeng = len(imgString)
                print("image data size:", imageLeng)
                currentTime = str(datetime.now())
                print("currentTime:", currentTime)
                if imageLeng > 10012:
                    url = "data:image/jpeg;base64,"+imgString
                    # save to mongo for share screen
                    saveDataToCollection('imagecontroller', { "imageURL": url, "size": len(url) }, GET_IMAGE)
                    #save file for testing
                    print("try to save image")
                    imgdata = base64.b64decode(imgString)
                    filename = currentTime +".jpg"  # I assume you have a way of picking unique filenames
                    with open(filename, 'wb') as f:
                        f.write(imgdata)

                        if run_from_ipython():
                            # img = mpimg.imread('1.jpg'), from file
                            i = io.BytesIO(imgdata)
                            i = mpimg.imread(i, format='JPG') # from memory, binary

                            # plt.imshow(i, interpolation='nearest')
                            imgplot = plt.imshow(i)# may be no difference
                            plt.pause(0.01)
                        else:
                            print("not ipython, so do no show image after saving")

                global numberOfImages
                numberOfImages += 1
                if numberOfImages == 2:
                    print("start to request testing image, aj.fits")
                    ImageController.selectFileToOpen(client)
            else:
                print("dummy response of select file request")

        #2.  remove it, may not be necessary for Browser, just alight with React JS Browser client
        client.remove('responses', {'_id': id}, callback=remove_callback)

    elif collection == "imagecontroller":
        print("grimmer imagecontroller added/changed")
        sessionID = SessionManager.getSuitableSession()
        docs = client.find(collection, selector={'sessionID': sessionID})
        total = len(docs)
        if total > 0:
            print("total doc:",total)
            firstDoc = docs[0]
            for doc in docs:
                docID = doc["_id"]
                print("loop image collection, id is", docID)
                print("image size:", len(doc["imageURL"]))
                if docID != id:
                    print("remove it")
                    client.remove('imagecontroller', {'_id': docID}, callback=remove_image_callback)
                    # global testimage
                    # testimage +=1
                    # if testimage ==1:
                    #     print("try 2nd image file")
                    #     ImageController.selectFileToOpen2(client)
                    #
                    # doc["comments"] = "apple"
                    # for testing client.update('imagecontroller', {'_id': docID}, {"name": "ggg"}, callback=update_callback)
                    # for testing
                    # client.update('imagecontroller', {'_id': docID}, doc, callback=update_callback)
                else:
                    print("not remove it")

                    # delete previous images

#TODO commmand response need to be deleted.
def added(collection, id, fields):
    print('* ADDED {} {}'.format(collection, id))
    handleAddedOrChanged(collection, id, fields)
    print('end added')


#  ADDED users vo5Eb7cG94waZmiGY
#   - FIELD username grimmer4

    # query the data each time something has been added to
    # a collection to see the data `grow`
    # all_lists = client.find('lists', selector={})
    # print('Lists: {}'.format(all_lists))
    # print('Num lists: {}'.format(len(all_lists)))

    # if collection == 'list' you could subscribe to the list here
    # with something like
    # client.subscribe('todos', id)
    # all_todos = client.find('todos', selector={})
    # print 'Todos: {}'.format(all_todos)

    # all_lists = client.find('tasks', selector={})
    # print('Tasks: {}'.format(all_lists))
    # print('Num lists: {}'.format(len(all_lists)))

def changed(collection, id, fields, cleared):
    print('CHANGED !!!: {} {}'.format(collection, id))
    # handleAddedOrChanged(collection, id, fields)

    # all_lists = client.find('tasks', selector={})
    # print('Tasks: {}'.format(all_lists))
    # print('Num lists: {}'.format(len(all_lists)))
    print('end changed')



    # conf.set('ddp', 'token', data['token'])
    # conf.update()

def subscription_response_callback(error):
    if error:
        print("sub fail")
        print(error)
    print("sub resp ok")

def subscription_image_callback(error):
    if error:
        print("sub2 fail")
        print(error)
    print("sub image ok2")
    ImageController.sendRegiserView(client)

def getSession_callback(error, result):
    if error:
        print(error)
        return
    print("in getSession_callback")
    print(result)
    SessionManager.set(result)
    print("get:", SessionManager.get())
    client.subscribe('commandResponse', [SessionManager.get()], callback=subscription_response_callback)
    client.subscribe('imagecontroller', [SessionManager.get()], callback=subscription_image_callback)
    # subscribe response
    # subscribe imageController
    # observe response, imageController

def getSession():
    print("try getSession")
    # empty params, so []
    client.call(getSessionCmd, [], getSession_callback)

def connected():
    print('* CONNECTED')
    # all_lists = client.find('tasks', selector={})
    # print('Tasks: {}'.format(all_lists))
    # print('Num lists: {}'.format(len(all_lists)))
    print('end connected, try login')
    client.login('grimmer4', "123456")
    print('setup collection')

def removed(collection, id):
    print('* REMOVED {} {}'.format(collection, id))

def on_logged_in(data):
    print('LOGGIN IN', data)


if run_from_ipython():
    print("is ipython, setupt matplotlib")
    plt.ion()
    plt.figure()
    plt.show()
else:
    print("not ipython")
# sys.exit()


# img = mpimg.imread('2.png')  #3s
#     # img = mpimg.imread('1.jpg') 3s
#
# imgplot = plt.imshow(img)
# plt.ion()
# plt.show()=

client.on('removed', removed)

client.on('changed', changed)
client.on('subscribed', subscribed)
client.on('unsubscribed', unsubscribed)
client.on('added', added)
client.on('connected', connected)
client.on('logged_in', on_logged_in)

client.connect()

# client.subscribe('publicLists')
getSession()
# client.subscribe('tasks')


# (sort of) hacky way to keep the client alive
# ctrl + c to kill the script
# while True:
#     try:
#         time.sleep(5)
#     except KeyboardInterrupt:
#         break
