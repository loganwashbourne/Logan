#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 
# Copyright 2015 <+YOU OR YOUR COMPANY+>.
# 
# This is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3, or (at your option)
# any later version.
# 
# This software is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this software; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street,
# Boston, MA 02110-1301, USA.
# 

import string
import numpy
import pmt
import time
from gnuradio import gr
from gnuradio import digital

class chat_sanitizer1(gr.basic_block):
    """
    This block will accept inputs through a member function,
    sanitize them (in this case, remove all non-printable characters)
    prepend a prefix, and send the string as a uint8 vector out on
    the message port named 'msg_out'.
    """
    ack = 0
    def __init__(self, prefix="user1", access_code=None):
        gr.basic_block.__init__(self,
            name="chat_sanitizer1",
            in_sig=[], # No streaming ports!
            out_sig=[])
        self.prefix = prefix
        # Register the message port
        self.message_port_register_out(pmt.intern('out'))
	self.message_port_register_in(pmt.intern('ack_in'))
	self.set_msg_handler(pmt.intern('ack_in'), self.ack_set)

        # access_code = digital.packet_utils.default_access_code
        #  1010110011011101101001001110001011110010100011000010000011111100
        if access_code:
            if not digital.packet_utils.is_1_0_string(access_code):
                raise ValueError, \
                    "Invalid access_code %r. Must be string of 1's and 0's" % (access_code,)

        self.access_code = access_code
	

    def ack_set(self,msg_pmt):
	msg = pmt.cdr(msg_pmt)
        msg_str = "".join([chr(x) for x in pmt.u8vector_elements(msg)])
	#print msg_str
	if msg_str == 'ACK':
            self.ack = 1;
	#print self.ack   
	
    def post_message(self, msg_str):
	if self.ack == 0:
	    """ Take a string, remove all non-printable characters,
	    prepend the prefix and post to the next block. """
	    # Do string sanitization:
	    msg_str = filter(lambda x: x in string.printable, msg_str)
	    send_str = "[{}] {}".format(self.prefix, msg_str)
	    count = 0;
	    # prepend AC to sent packet
	    if self.access_code:
	        (packed_access_code, padded) = digital.packet_utils.conv_1_0_string_to_packed_binary_string(self.access_code)
	        print self.access_code
	        print map(ord, packed_access_code)
	        print padded
	        send_str = packed_access_code + send_str

	    #print len(send_str)
	    #print send_str
	    # Create an empty PMT (contains only spaces):
	    send_pmt = pmt.make_u8vector(len(send_str), ord(' '))
	    # Copy all characters to the u8vector:
	    for i in range(len(send_str)):
	        pmt.u8vector_set(send_pmt, i, ord(send_str[i]))
	        #print ord(send_str[i])
	    # Send the message:
	    while self.ack != 1:
	        self.message_port_pub(pmt.intern('out'), pmt.cons(pmt.PMT_NIL, send_pmt))
		time.sleep(.06)
		count = count + 1
                if count == 6:
                    print 'Message not received by RX'
                    self.ack = 1
                print count
	    #print self.ack
	    self.ack = 0

class chat_receiver1(gr.basic_block):
    """ Inverse block to the chat_sanitizer: Receives a u8vector on the input,
    and prints it out nicely. """
    def __init__(self):
        gr.basic_block.__init__(self,
            name="chat_receiver1",
            in_sig=[], # No streaming ports!
            out_sig=[])
        # Register the message port
        self.message_port_register_in(pmt.intern('in'))
        self.set_msg_handler(pmt.intern('in'), self.handle_msg)
	self.message_port_register_out(pmt.intern('acknowledge'))

    def handle_msg(self, msg_pmt):
        """ Receiver a u8vector on the input port, and print it out. """
        # Collect metadata, convert to Python format:
        meta = pmt.to_python(pmt.car(msg_pmt))
        # Collect message, convert to Python format:
        msg = pmt.cdr(msg_pmt)
        # Make sure it's a u8vector
        if not pmt.is_u8vector(msg):
            print "[ERROR] Received invalid message type.\n"
            return
        # Convert to string:
        msg_str = "".join([chr(x) for x in pmt.u8vector_elements(msg)])
        # Just for good measure, and to avoid attacks, let's filter again:
        msg_str = filter(lambda x: x in string.printable, msg_str)
        # Print string, and if available, the metadata:
        print msg_str
	self.post_ack()
        if meta is not None:
            print "[METADATA]: ", meta

    def post_ack(self):
	send_ack = pmt.make_u8vector(3,ord(' '))
	ack_str = 'ACK'
	for i in range(len(ack_str)):
	    pmt.u8vector_set(send_ack, i, ord(ack_str[i]))
	self.message_port_pub(pmt.intern('acknowledge'), pmt.cons(pmt.PMT_NIL, send_ack))


############ Make this file work standalone -- This would usually not be done in
############ out-of-tree modules, just to demonstrate these blocks in the same file as they are
############ defined.
if __name__ == "__main__":
    import time
    # Create a flow graph
    tb = gr.top_block()
    # Create chat blocks
    chat_tx = chat_sanitizer1(prefix="DemoUser")
    chat_rx = chat_receiver1()
    # Connect them up
    tb.msg_connect(chat_tx, 'out', chat_rx, 'in')
    # Start flow graph
    tb.start()
    chat_str = ""
    print "======= Chat/Message Passing Tester. Please type a message (type /quit to exit) ========="
    try:
        while chat_str != "/quit":
            chat_str = raw_input('> ')
            chat_tx.post_message(chat_str)
            time.sleep(0.1)
    except KeyboardInterrupt:
        print "\n"
    except EOFError:
        print "\n"
    # Shut down flow graph
    tb.stop()
    # Wait for blocks to shut down
    tb.wait()
    print ">>> Done. Enjoy the message passing! <<<"
