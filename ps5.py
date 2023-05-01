import feedparser
import string
import time
import threading
from project_util import translate_html
from mtTkinter import *
from datetime import datetime
import pytz
import string


#======================
# Code for retrieving and parsing
# Google News feeds
#======================

def process(url):
    """
    Fetches news items from the rss url and parses them.
    Returns a list of NewsStory-s.
    """
    feed = feedparser.parse(url)
    entries = feed.entries
    ret = []
    for entry in entries:
        guid = entry.guid
        title = translate_html(entry.title)
        link = entry.link
        description = translate_html(entry.description)
        pubdate = translate_html(entry.published)

        try:
            pubdate = datetime.strptime(pubdate, "%a, %d %b %Y %H:%M:%S %Z")
            pubdate.replace(tzinfo=pytz.timezone("EST"))
            # pubdate = pubdate.astimezone(pytz.timezone('EST'))
            # pubdate.replace(tzinfo=None)
        except ValueError:
            pubdate = datetime.strptime(pubdate, "%a, %d %b %Y %H:%M:%S %z")

        newsStory = NewsStory(guid, title, description, link, pubdate)
        ret.append(newsStory)
    return ret


class NewsStory(object):
    def __init__(self, guid, title, description, link, pubdate):
        '''
        Initializes a NewsStory object'''
        self.guid = guid
        self.title = title
        self.description = description
        self.link = link 
        self.pubdate = pubdate
    
    def get_guid(self):
        return self.guid
    
    def get_title(self):
        return self.title
    
    def get_description(self):
        return self.description
    
    def get_link(self):
        return self.link
    
    def get_pubdate(self):
        return self.pubdate

#======================
# Triggers
#======================

class Trigger(object):
    def evaluate(self, story):
        """
        Returns True if an alert should be generated
        for the given news item, or False otherwise.
        """
        # DO NOT CHANGE THIS!
        raise NotImplementedError

# PHRASE TRIGGERS
class PhraseTrigger(Trigger):
    def __init__(self, phrase):
        self.phrase = phrase

    def is_phrase_in(self, text):
        # turn all letters into lowercase --> store each word as string item in a list
        phraselist = self.phrase.lower().split()

        # replace all the punctuation with spaces
        for character in string.punctuation:
            text = text.replace(character, ' ')

        # turn all letters in story to lowercase, split the words in the story
        text = text.lower().split()

        # if the first word of the letter is found
        if phraselist[0] in text:
            index = text.index(phraselist[0])
            # check if text is long enough to possibly contain the remaining words of the phrase
            if len(text) < index+len(phraselist):
                return False
            # check if the following words (until the len of the splitted words of phrase) match with the story
            for i in range(1,len(phraselist)):
                if phraselist[i] != text[index+i]:
                    return False
            return True

class TitleTrigger(PhraseTrigger):
    def __init__(self,phrase):
        PhraseTrigger.__init__(self,phrase)
    
    def evaluate(self, story):
        """
        Returns True if an alert should be generated
        for the given news item, or False otherwise.
        """
        title = story.get_title()
        return PhraseTrigger.is_phrase_in(self,title)

class DescriptionTrigger(PhraseTrigger):
    def __init__(self,phrase):
        PhraseTrigger.__init__(self,phrase)
    
    def evaluate(self, story):
        """
        Returns True if an alert should be generated
        for the given news item, or False otherwise.
        """
        des = story.get_description()
        return PhraseTrigger.is_phrase_in(self,des)


# TIME TRIGGERS
class TimeTrigger(Trigger):
    def __init__(self,time):
        time = datetime.strptime(time, "%d %b %Y %H:%M:%S")
        self.time = time.replace(tzinfo=pytz.timezone("EST"))

class BeforeTrigger(TimeTrigger):
    def evaluate(self, story):
        storytime = story.get_pubdate()
        if storytime.replace(tzinfo=pytz.timezone("EST")) < self.time:
            return True
        return False

class AfterTrigger(TimeTrigger):
    def evaluate(self, story):
        storytime = story.get_pubdate()
        if storytime.replace(tzinfo=pytz.timezone("EST")) > self.time:
            return True
        return False
        

# COMPOSITE TRIGGERS
class NotTrigger(Trigger):
    def __init__(self, trigger):
        self.trigg = trigger
    def evaluate(self, story):
        return not self.trigg.evaluate(story)

class AndTrigger(Trigger):
    def __init__(self, trig1, trig2):
        self.trig1 = trig1
        self.trig2 = trig2
    
    def evaluate(self,story):
        if self.trig1.evaluate(story) and self.trig2.evaluate(story):
            return True
        return False

class OrTrigger(Trigger):
    def __init__(self, trig1, trig2):
        self.trig1 = trig1
        self.trig2 = trig2
    
    def evaluate(self,story):
        if self.trig1.evaluate(story) or self.trig2.evaluate(story):
            return True
        return False


#======================
# Filtering
#======================

def filter_stories(stories, triggerlist):
    """
    Takes in a list of NewsStory instances.

    Returns: a list of only the stories for which a trigger in triggerlist fires.
    """
    storieswtrig = []
    for story in stories:
        for trigger in triggerlist:
            if trigger.evaluate(story):
                storieswtrig.append(story)
                break
    return storieswtrig


#======================
# User-Specified Triggers
#======================
def read_trigger_config(filename):
    """
    filename: the name of a trigger configuration file

    Returns: a list of trigger objects specified by the trigger configuration
        file.
    """
    trigger_file = open(filename, 'r')
    lines = []
    for line in trigger_file:
        line = line.rstrip()
        if not (len(line) == 0 or line.startswith('//')):
            lines.append(line)

    triggerdict = {}
    triggerlst = []
    for line in lines:
        trigdef = line.split(',')
        if trigdef[1] == 'TITLE':
            triggerdict[trigdef[0]] = TitleTrigger(trigdef[2])
        elif trigdef[1] == 'DESCRIPTION':
            triggerdict[trigdef[0]] = DescriptionTrigger(trigdef[2])
        elif trigdef[1] == 'AFTER':
            triggerdict[trigdef[0]] = AfterTrigger(trigdef[2])
        elif trigdef[1] == 'BEFORE':
            triggerdict[trigdef[0]] = BeforeTrigger(trigdef[2])
        elif trigdef[1] == 'AND':
            triggerdict[trigdef[0]] = AndTrigger(triggerdict[trigdef[2]],triggerdict[trigdef[3]])
        elif trigdef[1] == 'NOT':
            triggerdict[trigdef[0]] = NotTrigger(trigdef[2])
        elif trigdef[1] == 'OR':
            triggerdict[trigdef[0]] = OrTrigger(triggerdict[trigdef[2]],triggerdict[trigdef[3]])
        elif trigdef[0] == 'ADD':
            for i in range(1,len(trigdef)):
                triggerlst.append(triggerdict[trigdef[i]])
    return triggerlst            
            



SLEEPTIME = 120 #seconds -- how often we poll

def main_thread(master):
    try:
        triggerlist = read_trigger_config('triggers.txt')
        
        # Draws the popup window that displays the filtered stories
        # Retrieves and filters the stories from the RSS feeds
        frame = Frame(master)
        frame.pack(side=BOTTOM)
        scrollbar = Scrollbar(master)
        scrollbar.pack(side=RIGHT,fill=Y)

        t = "Google Top News"
        title = StringVar()
        title.set(t)
        ttl = Label(master, textvariable=title, font=("Helvetica", 18))
        ttl.pack(side=TOP)
        cont = Text(master, font=("Helvetica",14), yscrollcommand=scrollbar.set)
        cont.pack(side=BOTTOM)
        cont.tag_config("title", justify='center')
        button = Button(frame, text="Exit", command=root.destroy)
        button.pack(side=BOTTOM)
        guidShown = []
        def get_cont(newstory):
            if newstory.get_guid() not in guidShown:
                cont.insert(END, newstory.get_title()+"\n", "title")
                cont.insert(END, "\n---------------------------------------------------------------\n", "title")
                cont.insert(END, newstory.get_description())
                cont.insert(END, "\n*********************************************************************\n", "title")
                guidShown.append(newstory.get_guid())

        while True:

            print("Polling . . .", end=' ')
            # Get stories from Google's Top Stories RSS news feed
            stories = process("http://news.google.com/news?output=rss")

            stories = filter_stories(stories, triggerlist)

            list(map(get_cont, stories))
            scrollbar.config(command=cont.yview)

            print("Sleeping...")
            time.sleep(SLEEPTIME)

    except Exception as e:
        print(e)


if __name__ == '__main__':
    root = Tk()
    root.title("Some RSS parser")
    t = threading.Thread(target=main_thread, args=(root,))
    t.start()
    root.mainloop()

