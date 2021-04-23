from stmpy import * #Machine, Driver
from recognizer import *#recognize
from recorder import *#record, play
from walkietalkie import * #import text_to_speach
from text_to_speach import text_to_speach

def analyzeInput(input): #vet ikke om input skal være lydfil eller tekststring?
    #input = self.recognize()  --> hvis input er lydfil
    command = input.split()
    if command[0]=="play":
        text_to_speach.text_to_speach("Incoming message is: ")
        self.recorder.play() #hvordan vet den om det er riktig output.wav?
        #test: print("Incoming message is: ",message)
        #burde vi hente ut hvem det er fra og?
        # if ny?input = "next": denne må jo ta inn en ny lydfil... se stm
        return
    elif command[0]=="replay":
        if len(command) == 1: #command should be 2 words
            text_to_speach.text_to_speach("Name not found. Use command: Replay name. Try again")
            return
        for name in colleaguenames: #dict til christopher
            if name == command[1]:
                #hent siste mld fra name-personen fra server
                message_from_name = "blablabla"
                print("Last message from ", name, "is: ", message_from_name)
                text = "Last message from ", name, "is: ", message_from_name
                text_to_speach.text_to_speach(text)  #eller bare bruke play?
                return
    elif command[0] == "send":
        if len(command) == 1:
            print("Name not found. Use command: send name. Try again")
            return
        name = command[1]
        topic = colleaguenames[name] #avhenger av dict til christopher
        self.walkietalkie.start_recording() #evt bruke rett fra recorder?
        self.recorder.stop()
        self.recorder.process()
        self.walkietalkie.send_data()
        text = "Message has been sent to" + name
        text_to_speach.text_to_speach(text)
        print("Message has been sent to", name)
        return
    elif command[0]=="help":
        #send message help til alle nurses&doctorer med forhåndslagd mld?
        #send_data() kan denne brukes her? hvor setter man mld i såfall
        print("Help is requested")
    else:
        print("Invalid input")
        return



#tester
colleaguenames = {"anne": "topicname"}
print("1")
analyzeInput("send")
print("2")
analyzeInput("send anne")
print("3")
analyzeInput("play")
print("4")
analyzeInput("replay")
print("5")
analyzeInput("replay anne")
print("6")
analyzeInput("hjelp")
print("7")
analyzeInput("help")