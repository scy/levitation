#!/usr/bin/env python


# Hi, and welcome to the code.
# This is currently PoC quality, and I'm no Python God either.
# Patches are encouraged, fork me on GitHub.


import xml.dom.minidom
import xml.parsers.expat
from calendar import timegm
import codecs
import datetime
import os
import re
import socket
import struct
import sys
import time
import urlparse
from optparse import OptionParser

# The encoding for input, output and internal representation. Leave alone.
ENCODING = 'UTF-8'
# The XML namespace we support.
XMLNS = 'http://www.mediawiki.org/xml/export-0.4/'
# Namespace separator for Expat.
NSSEPA = ' '


def parse_args(args):
	usage = 'Usage: git init --bare repo && bzcat pages-meta-history.xml.bz2 | \\\n' \
	        '       %prog [options] | GIT_DIR=repo git fast-import | sed \'s/^progress //\''
	parser = OptionParser(usage=usage)
	parser.add_option("-m", "--max", dest="IMPORT_MAX", metavar="IMPORT_MAX",
			help="Specify the maxium pages to import, -1 for all (default: 100)",
			default=100, type="int")
	parser.add_option("-d", "--deepness", dest="DEEPNESS", metavar="DEEPNESS",
			help="Specify the deepness of the result directory structure (default: 3)",
			default=3, type="int")
	parser.add_option("-c", "--committer", dest="COMMITTER", metavar="COMITTER",
			help="git \"Committer\" used while doing the commits (default: \"Levitation <levitation@scytale.name>\")",
			default="Levitation <levitation@scytale.name>")
	parser.add_option("-w", "--wikitime", dest="WIKITIME",
			help="When set, the commit time will be set to the revision creation, not the current system time", action="store_true",
			default=False)
	parser.add_option("-M", "--metafile", dest="METAFILE", metavar="META",
			help="File for storing meta information (17 bytes/rev) (default: .import-meta)",
			default=".import-meta")
	parser.add_option("-C", "--commfile", dest="COMMFILE", metavar="COMM",
			help="File for storing comment information (257 bytes/rev) (default: .import-comm)",
			default=".import-comm")
	parser.add_option("-U", "--userfile", dest="USERFILE", metavar="USER",
			help="File for storing author information (257 bytes/author) (default: .import-user)",
			default=".import-user")
	parser.add_option("-P", "--pagefile", dest="PAGEFILE", metavar="PAGE",
			help="File for storing page information (257 bytes/page) (default: .import-page)",
			default=".import-page")
	(options, args) = parser.parse_args(args)
	return (options, args)

def tzoffset():
	r = time.strftime('%z')
	if r == '' or r == '%z':
		return None
	return r

def tzoffsetorzero():
	r = tzoffset()
	if r == None:
		return '+0000'
	return r

def singletext(node):
	if len(node.childNodes) == 0:
		return ''
	if len(node.childNodes) != 1:
		raise Exception('singletext has wrong number of children' + node.toxml())
	if node.childNodes[0].nodeType != node.TEXT_NODE:
		raise Exception('singletext child is not text')
	return node.childNodes[0].data

def asciiize_char(s):
	r = ''
	for x in s.group(0):
		r += '.' + x.encode('hex').upper()
	return r

def asciiize(s):
	return re.sub('[^A-Za-z0-9_ ()-]', asciiize_char, s)

def out(text):
	sys.stdout.write(text)

def progress(text):
	out('progress ' + text + '\n')
	sys.stdout.flush()

class Meta:
	def __init__(self, file):
		self.struct = struct.Struct('LLLLB')
		self.maxrev = -1
		self.fh = open(file, 'wb+')
		self.domain = 'unknown.invalid'
		self.nstoid = self.idtons = {}
	def write(self, rev, time, page, author, minor):
		flags = 0
		if minor:
			flags += 1
		if author.isip:
			flags += 2
		if author.isdel:
			flags += 4
		data = self.struct.pack(
			rev,
			timegm(time.utctimetuple()),
			page,
			author.id,
			flags
			)
		self.fh.seek(rev * self.struct.size)
		self.fh.write(data)
		if self.maxrev < rev:
			self.maxrev = rev
	def read(self, rev):
		self.fh.seek(rev * self.struct.size)
		data = self.fh.read(self.struct.size)
		tuple = self.struct.unpack(data)
		d = {
			'rev':    tuple[0],
			'epoch':  tuple[1],
			'time':   datetime.datetime.utcfromtimestamp(tuple[1]),
			'page':   tuple[2],
			'user':   tuple[3],
			'minor':  False,
			'isip':   False,
			'isdel':  False,
			}
		if d['rev'] != 0:
			d['exists'] = True
		else:
			d['exists'] = False
		d['day'] = d['time'].strftime('%Y-%m-%d')
		flags = tuple[4]
		if flags & 1:
			d['minor'] = True
		if flags & 2:
			d['isip'] = True
			d['user'] = socket.inet_ntoa(struct.pack('!I', tuple[3]))
		if flags & 4:
			d['isdel'] = True
		return d

class StringStore:
	def __init__(self, file):
		self.struct = struct.Struct('Bb255s')
		self.maxid = -1
		self.fh = open(file, 'wb+')
	def write(self, id, text, flags = 1):
		if len(text) > 255:
			progress('warning: trimming %s bytes long text: 0x%s' % (len(text), text.encode('hex')))
			text = text[0:255].decode(ENCODING, 'ignore').encode(ENCODING)
		data = self.struct.pack(len(text), flags, text)
		self.fh.seek(id * self.struct.size)
		self.fh.write(data)
		if self.maxid < id:
			self.maxid = id
	def read(self, id):
		self.fh.seek(id * self.struct.size)
		packed = self.fh.read(self.struct.size)
		data = None
		if len(packed) < self.struct.size:
			# There is no such entry.
			d = {'len': 0, 'flags': 0, 'text': ''}
		else:
			data = self.struct.unpack(packed)
			d = {
				'len':   data[0],
				'flags': data[1],
				'text':  data[2][0:data[0]]
				}
		return d

class User:
	def __init__(self, node, meta):
		self.id = -1
		self.name = None
		self.isip = self.isdel = False
		if node.hasAttribute('deleted') and node.getAttribute('deleted') == 'deleted':
			self.isdel = True
		for lv1 in node.childNodes:
			if lv1.nodeType != lv1.ELEMENT_NODE:
				continue
			if lv1.tagName == 'username':
				self.name = singletext(lv1).encode(ENCODING)
			elif lv1.tagName == 'id':
				self.id = int(singletext(lv1))
			elif lv1.tagName == 'ip':
				# FIXME: This is so not-v6-compatible it hurts.
				self.isip = True
				try:
					self.id = struct.unpack('!I', socket.inet_aton(singletext(lv1)))[0]
				except (socket.error, UnicodeEncodeError):
					# IP could not be parsed. Leave ID as -1 then.
					pass
		if not (self.isip or self.isdel):
			meta['user'].write(self.id, self.name)

class Revision:
	def __init__(self, node, page, meta):
		self.id = -1
		self.minor = False
		self.timestamp = self.text = self.comment = self.user = None
		self.page = page
		self.meta = meta
		self.dom = node
		for lv1 in self.dom.childNodes:
			if lv1.nodeType != lv1.ELEMENT_NODE:
				continue
			if lv1.tagName == 'id':
				self.id = int(singletext(lv1))
			elif lv1.tagName == 'timestamp':
				self.timestamp = datetime.datetime.strptime(singletext(lv1), "%Y-%m-%dT%H:%M:%SZ")
			elif lv1.tagName == 'contributor':
				self.user = User(lv1, self.meta)
			elif lv1.tagName == 'minor':
				self.minor = True
			elif lv1.tagName == 'comment':
				self.comment = singletext(lv1)
			elif lv1.tagName == 'text':
				self.text = singletext(lv1)
	def dump(self):
		self.meta['meta'].write(self.id, self.timestamp, self.page, self.user, self.minor)
		if self.comment:
			self.meta['comm'].write(self.id, self.comment.encode(ENCODING))
		mydata = self.text.encode(ENCODING)
		out('blob\nmark :%d\ndata %d\n' % (self.id + 1, len(mydata)))
		out(mydata + '\n')

class Page:
	def __init__(self, meta):
		self.title = self.fulltitle = ''
		self.nsid = 0
		self.id = -1
		self.meta = meta
	def setTitle(self, title):
		self.fulltitle = title
		split = self.fulltitle.split(':', 1)
		if len(split) > 1 and (split[0] in self.meta['meta'].nstoid):
			self.nsid = self.meta['meta'].nstoid[split[0]]
			self.title = split[1]
		else:
			self.nsid = self.meta['meta'].nstoid['']
			self.title = self.fulltitle
	def setID(self, id):
		self.id = id
		self.saveTitle()
	def saveTitle(self):
		if self.id != -1 and self.title != '':
			self.meta['page'].write(self.id, self.title, self.nsid)
	def addRevision(self, dom):
		r = Revision(dom, self.id, self.meta)
		r.dump()

class XMLError(ValueError):
	pass

class CancelException(StandardError):
	pass

class ParserHandler:
	def __init__(self, writer):
		self.writer = writer

class ExpatHandler(ParserHandler):
	def run(self, what):
		self.expat = xml.parsers.expat.ParserCreate(namespace_separator = NSSEPA)
		self.expat.StartElementHandler  = self.startElement
		self.expat.EndElementHandler    = self.endElement
		self.expat.CharacterDataHandler = self.characters
		self.expat.ParseFile(what)
	def nsSplit(self, name):
		s = name.split(NSSEPA, 1)
		if len(s) == 2:
			return (s[0], s[1])
		else:
			return ('', s[0])
	def startElement(self, name, attrs):
		name = self.nsSplit(name)
		self.writer.startElement(name, attrs)
	def endElement(self, name):
		name = self.nsSplit(name)
		self.writer.endElement(name)
	def characters(self, data):
		self.writer.characters(data)

class BlobWriter:
	def __init__(self, meta):
		self.imported = 0
		self.cancelled = False
		self.meta = meta
		self.parser = self.dom = self.page = None
		firsthandler = self.in_doc
		self.handler = firsthandler
		self.handlers = [firsthandler]
		self.hpos = 0
		self.text = None
	def parse(self, parser):
		self.parser = parser(self)
		try:
			self.parser.run(sys.stdin)
		except CancelException:
			if not self.cancelled:
				raise
	def nsSplit(self, name):
		s = name.split(NSSEPA, 1)
		if len(s) == 2:
			return (s[0], s[1])
		else:
			return ('', s[0])
	def runHandler(self, name, attrs):
		# Check the namespace.
		if not name[0] == XMLNS:
			if self.hpos > 0:
				# If this is not the root element, simply ignore it.
				return
			else:
				# If this is the root element, refuse to parse it.
				raise XMLError('XML document needs to be in MediaWiki Export Format 0.4')
		# If there is no handler, this tag shall be ignored.
		if self.handler == None:
			return
		# Run the handler and return its return value (possibly a sub-handler).
		return self.handler(name, attrs)
	def startElement(self, name, attrs):
		# If capturing, add a new element.
		if self.dom:
			self.finishText()
			self.currentnode = self.currentnode.appendChild(self.dom.createElementNS(name[0], name[1]))
			for k, v in attrs.iteritems():
				sk = self.nsSplit(k)
				self.currentnode.setAttributeNS(sk[0], sk[1], v)
		# Run the handler and add the sub-handler to the handler stack.
		nexthandler = self.runHandler(name, attrs)
		self.handlers.append(nexthandler)
		self.hpos += 1
		self.handler = nexthandler
	def endElement(self, name):
		# If capturing, point upwards.
		if self.dom:
			self.finishText()
			self.currentnode = self.currentnode.parentNode
		# Tell the handler that its element is done.
		self.runHandler(name, False)
		# Remove the sub-handler.
		self.handlers.pop()
		self.hpos -= 1
		# Check whether we have more closing tags than opening.
		if self.hpos < 0:
			raise XMLError('more closing than opening tags')
		# Update the current handler.
		self.handler = self.handlers[self.hpos]
	def characters(self, content):
		# If capturing, append content to internal text buffer.
		if self.dom:
			if self.text == None:
				self.text = content
			else:
				self.text += content
	def finishText(self):
		# Called before something that ends a text node is added.
		if not self.text == None:
			self.currentnode.appendChild(self.dom.createTextNode(self.text))
			self.text = None
	def captureStart(self, name):
		self.dom = xml.dom.getDOMImplementation().createDocument(name[0], name[1], None)
		self.currentnode = self.dom.documentElement
	def captureGet(self):
		dom = self.dom
		self.dom = None
		return dom.documentElement
	def in_doc(self, name, attrs):
		if name[1] == 'mediawiki':
			return self.in_mediawiki
		else:
			raise XMLError('document tag is not <mediawiki>')
	def in_mediawiki(self, name, attrs):
		if name[1] == 'siteinfo':
			return self.in_siteinfo
		if name[1] == 'page':
			self.page = Page(self.meta)
			return self.in_page
	def in_siteinfo(self, name, attrs):
		if name[1] == 'base':
			self.captureStart(name)
			return self.in_base
		elif name[1] == 'namespaces':
			return self.in_namespaces
	def in_base(self, name, attrs):
		if attrs == False:
			self.meta['meta'].domain = urlparse.urlparse(singletext(self.captureGet())).hostname.encode(ENCODING)
	def in_namespaces(self, name, attrs):
		if name[1] == 'namespace':
			self.captureStart(name)
			self.nskey = int(attrs['key']) # FIXME: not namespace-safe?
			return self.in_namespace
	def in_namespace(self, name, attrs):
		if attrs == False:
			v = singletext(self.captureGet()).encode(ENCODING)
			self.meta['meta'].idtons[self.nskey] = v
			self.meta['meta'].nstoid[v] = self.nskey
	def in_page(self, name, attrs):
		if attrs == False:
			self.imported += 1
			max = self.meta['options'].IMPORT_MAX
			if max > 0 and self.imported >= max:
				self.cancelled = True
				raise CancelException()
		else:
			if name[1] == 'title':
				self.captureStart(name)
				return self.in_title
			if name[1] == 'id':
				self.captureStart(name)
				return self.in_page_id
			if name[1] == 'revision':
				self.captureStart(name)
				return self.in_revision
	def in_title(self, name, attrs):
		if attrs == False:
			self.page.setTitle(singletext(self.captureGet()).encode(ENCODING))
			progress('   ' + self.page.fulltitle)
	def in_page_id(self, name, attrs):
		if attrs == False:
			self.page.setID(int(singletext(self.captureGet())))
	def in_revision(self, name, attrs):
		if attrs == False:
			self.page.addRevision(self.captureGet())

class Committer:
	def __init__(self, meta):
		self.meta = meta
		if tzoffset() == None:
			progress('warning: using %s as local time offset since your system refuses to tell me the right one;' \
				'commit (but not author) times will most likely be wrong' % tzoffsetorzero())
	def work(self):
		rev = commit = 1
		day = ''
		while rev <= self.meta['meta'].maxrev:
			meta = self.meta['meta'].read(rev)
			rev += 1
			if not meta['exists']:
				continue
			page = self.meta['page'].read(meta['page'])
			comm = self.meta['comm'].read(meta['rev'])
			namespace = asciiize('%d-%s' % (page['flags'], self.meta['meta'].idtons[page['flags']]))
			title = page['text']
			subdirtitle = ''
			for i in range(0, min(self.meta['options'].DEEPNESS, len(title))):
				subdirtitle += asciiize(title[i]) + '/'
			subdirtitle += asciiize(title)
			filename = namespace + '/' + subdirtitle + '.mediawiki'
			if meta['minor']:
				minor = ' (minor)'
			else:
				minor = ''
			msg = comm['text'] + '\n\nLevitation import of page %d rev %d%s.\n' % (meta['page'], meta['rev'], minor)
			if commit == 1:
				fromline = ''
			else:
				fromline = 'from :%d\n' % (commit - 1)
			if day != meta['day']:
				day = meta['day']
				progress('   ' + day)
			if meta['isip']:
				author = meta['user']
				authoruid = 'ip-' + author
			elif meta['isdel']:
				author = '[deleted user]'
				authoruid = 'deleted'
			else:
				authoruid = 'uid-' + str(meta['user'])
				author = self.meta['user'].read(meta['user'])['text']
			# Check which committime should be used
			if self.meta['options'].WIKITIME:
				# Use the committime read from the dumpfile
				committime = meta['epoch']
				offset = '+0000'
			else:
				# Use the current systemtime
				committime = time.time()
				offset = tzoffsetorzero()
			out(
				'commit refs/heads/master\n' +
				'mark :%d\n' % commit +
				'author %s <%s@git.%s> %d +0000\n' % (author, authoruid, self.meta['meta'].domain, meta['epoch']) +
				'committer %s %d %s\n' % (self.meta['options'].COMMITTER, committime, offset) +
				'data %d\n%s\n' % (len(msg), msg) +
				fromline +
				'M 100644 :%d %s\n' % (meta['rev'] + 1, filename)
				)
			commit += 1


(options, _args) = parse_args(sys.argv[1:])

meta = {
	'options': options,
	'meta': Meta(options.METAFILE),
	'comm': StringStore(options.COMMFILE),
	'user': StringStore(options.USERFILE),
	'page': StringStore(options.PAGEFILE),
	}

progress('Step 1: Creating blobs.')
BlobWriter(meta).parse(ExpatHandler)

progress('Step 2: Writing commits.')
Committer(meta).work()
