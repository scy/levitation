#!/usr/bin/env python

import xml.dom.minidom
from xml.parsers.expat import ParserCreate
import codecs
import datetime
import os
import sys
import bz2

READ_SIZE = 10240000
DUMP_PATTERN = '%Y-%m-%d-%H-%M-%S-'
DUMP_REVPATTERN = '%010d'
DUMP_LEVELS = 4
ENCODING = 'UTF-8'

def singletext(node):
	if len(node.childNodes) == 0:
		return ''
	if len(node.childNodes) != 1:
		raise Exception('singletext has wrong number of children' + node.toxml())
	if node.childNodes[0].nodeType != node.TEXT_NODE:
		raise Exception('singletext child is not text')
	return node.childNodes[0].data

class Revision:
	def __init__(self, node):
		self.id = -1
		self.minor = False
		self.timestamp = self.text = None
		self.dom = node
		for lv1 in self.dom.childNodes:
			if lv1.nodeType != lv1.ELEMENT_NODE:
				continue
			if lv1.tagName == 'id':
				self.id = int(singletext(lv1))
			elif lv1.tagName == 'timestamp':
				self.timestamp = datetime.datetime.strptime(singletext(lv1), "%Y-%m-%dT%H:%M:%SZ")
			elif lv1.tagName == 'minor':
				self.minor = True
			elif lv1.tagName == 'text':
				self.text = singletext(lv1)
	def dump(self, title):
		components = self.timestamp.strftime(DUMP_PATTERN).split('-', DUMP_LEVELS)
		filename = components.pop() + (DUMP_REVPATTERN % self.id) + '.mediawiki'
		dir = os.sep.join(components)
		if not os.path.isdir(dir):
			os.makedirs(dir)
		fh = bz2.BZ2File(os.path.join(dir, filename), 'w')
		fh.write("%s\n" % title.encode(ENCODING))
		fh.write(self.dom.toxml().encode(ENCODING))
		fh.close()

class Page:
	def __init__(self, xmlstring):
		self.revisions = []
		self.id = -1
		self.title = ''
		self.dom = xml.dom.minidom.parseString(xmlstring.encode(ENCODING))
		for lv1 in self.dom.documentElement.childNodes:
			if lv1.nodeType != lv1.ELEMENT_NODE:
				continue
			if lv1.tagName == 'title':
				self.title = singletext(lv1)
			elif lv1.tagName == 'id':
				self.id = int(singletext(lv1))
			elif lv1.tagName == 'revision':
				self.revisions.append(Revision(lv1))
	def dump(self):
		print '   ' + self.title.encode(ENCODING)
		for revision in self.revisions:
			revision.dump(self.title)

class XMLChunker:
	def __init__(self, filename):
		self.text = self.xml = None
		self.inpage = False
		self.startbyte = self.readbytes = 0
		self.fh = codecs.open(filename, 'r', ENCODING)
		self.expat = ParserCreate(ENCODING)
		self.expat.StartElementHandler = self.find_page
	def parse(self):
		while True:
			self.text = self.fh.read(READ_SIZE)
			encoded = self.text.encode(ENCODING)
			if not self.text:
				break
			self.startbyte = 0
			self.expat.Parse(encoded)
			if self.inpage:
				self.xml += self.text.encode(ENCODING)[self.startbyte:].decode(ENCODING)
			self.readbytes += len(encoded)
		self.expat.Parse('', True)
	def find_page(self, name, attrs):
		if name == 'page':
			self.inpage = True
			self.expat.StartElementHandler = None
			self.expat.EndElementHandler = self.find_pageend
			self.startbyte = self.expat.CurrentByteIndex - self.readbytes
			self.xml = u''
	def find_pageend(self, name):
		if name == 'page':
			if not self.inpage:
				raise Exception('not in page!')
			self.inpage = False
			self.expat.StartElementHandler = self.find_page
			self.expat.EndElementHandler = None
			self.xml += self.text.encode(ENCODING)[self.startbyte:self.expat.CurrentByteIndex-self.readbytes].decode(ENCODING) + '</' + name + '>'
			Page(self.xml).dump()

print "Step 1: Chunking by date."
xc = XMLChunker(sys.argv[1])
xc.parse()
