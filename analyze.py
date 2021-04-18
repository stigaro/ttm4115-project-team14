from os import system
#from stmpy import Machine, Driver


#hallo endring
def analyzeInput(input):
    command = input.split() #splitter alle ordene, Første ord blir keyword, input[0]
    if command[0]=="play":
        message = "hei beskjed blabla" #hente siste/uleste message fra server
        print("Incoming message is: ",message) #printer i stedenfor play, nå før play fungerer
        #hvordan gjør vi det med at next kan skje etter play
        #burde vi hente ut hvem det er fra og?
        # if ny?input = "next":
        return
    elif command[0]=="replay":
        if len(command) == 1:
            print("Who would you like to replay last message of? Use command: Replay name. Try again")
            return
        for name in colleaguenames: #dict eller liste
            if name == command[1]:
                #hent siste mld fra name-personen fra server
                message_from_name = "blablabla"
                print("Last message from ", name, "is: ", message_from_name) #ser for meg den spiller av siste mld fra den personen, hentet fra server
                return

    elif command[0] == "send":
        if len(command) == 1:
            print("Who would you like to send message to? Use command: send name. Try again")
            return
        name = command[1]
        topic = colleaguenames[name] #finne topic som hører til name
        #recording() #kalle record-funksjonen
        #send(recording, topic) #noe ala dette, sende til broker da?
        print("Message has been sendt to", name)
        return
    elif command[0]=="help":
        #send message help til alle nurses&doctorer med forhåndslagd mld
        print("Help is requested")
    else:
        print("Invalid input")
        return


#trenger: send(recordfile, topic) ,recording(), hente_mld_fra_server()

def incoming_message():
    blinking() #koble til et lys...
    sound_pip() #i steden for vibrering siden pc?
    return

#tester
colleaguenames = {"anne": "topicname"}
analyzeInput("send")
analyzeInput("send anne")
analyzeInput("play")
analyzeInput("replay")
analyzeInput("replay anne")
analyzeInput("hjelp")
analyzeInput("help")
