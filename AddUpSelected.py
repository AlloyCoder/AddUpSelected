"""
Program: AddupSelected.py
Author: AlloyCoder (with GPT-4 assistance)
Version: 1.08
Release Date: 9/18/2023
License: The Unlicense (Unrestricted public domain)
Developed using Notepad++ v8.5.6 and its PythonScript v2 plug-in which uses Python Version: 2.7.18

Purpose:
    This script serves as a plug-in for the Notepad++ editor, designed to sum up numbers within the selected text range. 
    It aims to provide an intuitive utility for everyday use, focusing on common decimal notation, negative numbers,    
    dollar amounts, and proper comma-separated thousands-grouping. 
    Anything reminiscent of arithmetic will be ignored and not counted.  Lots of other characters like () [] I consider neutral and valid. Yes, this is highly subjective. 
    
Usage:
    Upon successful execution, a pop-up window displays the total sum.
    The sum is always copied to the clipboard as "Selected Sum = 100.00".
    Additional pop-up notifications appear if negative numbers or numbers with too many digits were encountered in the selection.
    
Features:
    - Supports arbitrary precision up to 60 decimal places (set it with getcontext().prec= )
    - Recognizes only the period (".") as the decimal separator.
    - Handles negative numbers and optional dollar signs.
    - Filters out numbers with ambiguous formatting or characters.
    - Multiple negative signs invalidate a number.  We're not doing arithmetic, just removing plausibly neutral characters from numbers,
       like [], (), $, trailing *, etc. See examples below.  
       Trailing asterisks are assumed to be neutral footnote markers, not multiplication signs. 
       
    -  As of v1.06, powers-of-ten exponents (scientific notation) are allowed. 
       This only allows exponent notation; other "numbers" that the Decimal library allows, like "Infinity" and "NaN" will not pass our pre-screening.
       The maximum and minimum exponents are determined by the Emax and Emin attributes of the context. 
       By default, these are set to:   context.Emin = -999999     context.Emax = 999999
       We can compare the output in edge cases by using e.g.   https://www.mathsisfun.com/calculator-precision.html
           
Notes:
        This script was inspired by the TextFX number add-up plugin, of which no 64-bit version exists yet for Notepad++. 
        Notepad++'s Python scripting plug-in is limited to using Python version 2.7
        Future To Dos: 
            Create checks for numbers with huge amounts of zeroes that are candidates for forcing scientific notation output strings without information loss.
"""

# Test examples: 
#
#            7.     " -$10.00,  "   +$700.-----  ,   (00.100),    $1,000,000.-- ,   "199.99*",  "1"   and   -$$9;      " [-$400.0-;]      [-[$600*]*]    +++[[500]],   [[100.----------------*]*], 
#
# Test: all numbers on the above line are considered valid for our purposes and should sum to:  Selected Sum = 1000489.09 
#
#           
#  Numbers below are too ambiguous, e.g. could be intended as calculations, IP addresses, etc. so should result in "No selected valid numbers were found."  
#
#       ~3172      "9(99)"    10,0.123  ,   2008-10-09,   ,  "   $48.00/year  " ,   70,00,00.00    -[-[40]]   7*7    11?   46.58%     1.1.0.168    5x   10-1     ]7[   *9      =25
#
#  Numbers below are examples of acceptable scientific notation input. 
#
#      +"7.89101112131415E-12"       [231.1232132312E+12]     [1.00001E30]    "+17E39"    [+++((721.4121001E39))]  
#
#   Should sum to:      738412100101000010000000000231123213231200.00000000000789101112131415
#       


#from Npp import editor, notepad
#from decimal import Decimal, InvalidOperation, localcontext 
#import re
#import time

from Npp import *
from decimal import Decimal, getcontext, InvalidOperation, localcontext
import subprocess
import re
import time

MAX_PRECISIONDIGITS = 200
DO_COPY_TO_CLIPBOARD = True
EXTRA_NOTIFICATION_INFO = True
DO_PROFILING = False

# Pre-compiled regular expression for number matching.
DIGIT_RE = re.compile(r'[0-9]')    # Match anything that is a decimal digit. 
NON_DIGITS_RE = re.compile(r"[^\d]")   # match anything not a digit. 
ALPHASCI_CHAR_RE = re.compile(r"[a-df-zA-DF-Z]")   # match alphabetic except e and E 
ANY_DISQUALIFIER_RE = re.compile(r"[!#%&:<>?@_|\^\\\/~=\a]")  #match anything that's a subjectrively disqualifying

# This regex matches numbers with proper thousands separators and a period as the decimal separator.
COMMA_NUM_RE = re.compile(r"^\d{1,3}(,\d{3})*(\.\d+)?$")  
EXPONENT_E_RE = re.compile(r'[Ee]')  #searcing for an exponent 
STRIPPABLE_CHAR_RE = re.compile(r"[\$\(\)\*\+\,\-\'\"\;\[\]]")    # Potentially valid, neutral characters: semicolon, comma, dollar sign, parentheses, brackets, plus, minus, asterisk, single and double quotes. 

# Global counters 
skipped_due_to_precision = 0
conversion_fail_count = 0    

# Note - these can be recognized by the arbitrary precision Decimal library. Since we exclude all letters we don't need check for these.
# special_strings = {"infinity", "-infinity", "+infinity", "nan", "snan", "inf", "-inf"}

# Copy text to clipboard
def copy_to_clipboard(text):
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = subprocess.SW_HIDE
    subprocess.Popen(['clip'], stdin=subprocess.PIPE, startupinfo=startupinfo).communicate(text.encode('utf-8'))
    

    
def parse_generic_number(num_str):
    """
    Validates and parses a given number string and returns a Decimal object,
    
    :param str num_str: The number string to parse.
    :return: Parsed Decimal object, or None if invalid.
    :rtype: Decimal or None
    """    
    global skipped_due_to_precision
    global conversion_fail_count
            
    sign = 1
    minus_count = 0 
        
    # Pre-check if any stripping or processing of valid characters is needed. 
    # Peel potentially nested [] and () around a number, leading +, and trailing * asterisks, then count up all valid minus signs encountered. 
    if STRIPPABLE_CHAR_RE.search(num_str): 
        prev_length = -1
        while len(num_str) != prev_length:
            prev_length = len(num_str)
            num_str = num_str.rstrip("])*;,\'\"").lstrip("+$(['\'\"")    # strip *,],);,, from right, $,+,(,[ from left, and  both ' and " from around a number.                         
            if num_str.startswith('-'):  
                num_str = num_str[1:]  # Remove a leading '-' and note it as a minus.                 
                minus_count += 1        # log the - occurrence.
                
        # Handle negative numbers 
        if minus_count == 1: 
            sign = -1        
        elif minus_count > 1:    # Multiple negation is ambiguous. We're not doing arithmetic.
            return None             # There may still be invalid minuses or dashes embedded deeper in. Decimal() catches those.
    
    #  Handle decimal points and any trailing dashes which possibly signifyi zeroes after the decimal point.
    #   Very specific.  100--  is seen as too ambiguous,  but 23.--   and  100.0--  and 555.   are valid.  
    decimaldot_count = num_str.count('.')    
    
    exponent_present = EXPONENT_E_RE.search(num_str) 
    
    # Trailing dashes signify zeroes if there is a decimal point. Multiple decimal points are disqualifying, but Decimal() conversion should take care of that. 
    if (num_str.endswith('-') and (decimaldot_count == 0  or  exponent_present)):
        return None  # Invalid number e.g. " 17-  or  1.12312E48-
        
    if (decimaldot_count > 1):
        return None #invalid number e.g. 1.2.23.23
    
    if not exponent_present and  decimaldot_count == 1 and num_str.endswith('-'):
        num_str = num_str.rstrip('-')  + "0"   # Numbers like 7.--   become 7.0.  
            
    # Validate proper thousands separators. 
    if "," in num_str:
        if not COMMA_NUM_RE.match(num_str):
            return None                                
        num_str = num_str.replace(",", "")   # We have to remove even proper separator commas because Decimal doesn't allow them. 
        
    # Check if the total length might exceed our precision capability. 
    if len(num_str) >= MAX_PRECISIONDIGITS:
        skipped_due_to_precision += 1 
        return None
        
    # Final conversion. We handled the sign ourselves.
    try:        
        return sign * Decimal(num_str)
    except InvalidOperation:
        #print("Parse: ########### Failed to convert: {}".format(num_str))   # Extra logging. Development only. 
        conversion_fail_count += 1        
        return None



# An obscure python optimization: pre-define the call you're going to make , a possible 'local variable optimization'.    
DIGIT_SEARCH = DIGIT_RE.search

def is_potentially_valid_number(num_string):
    """
    Check if a given string is potentially a valid number for further parsing.
    :param str num_string: The string to check.
    :return: True if potentially valid, otherwise False.
    :rtype: bool
    """
    # Skip this string if it contains no decimal digits.
    if not DIGIT_SEARCH(num_string): 
        return False
        
    # Skip this string if it contains any letters of the alphabet (but e and E are allowed for exponents).
    if ALPHASCI_CHAR_RE.search(num_string): 
        return False
                                      
    # Ignore all numbers with additional disqualifying ambiguous characters.
    if ANY_DISQUALIFIER_RE.search(num_string): 
        return False
    
    return True


# Pauses the script until the system timer rolls over to a new value, ensuring more accurate profiling.
def align_the_timer():
    time_counter = time.time()
    while time_counter == time.time():
        pass
    time_counter = time.time()
    while time_counter == time.time():
        pass 
    return


# Main code 

with localcontext() as ctx:

    ctx.prec = MAX_PRECISIONDIGITS
    if DO_PROFILING:
        align_the_timer()    # trick to always start on a time() change, potentially aligning for more consistent results.
        start_time = time.time()     #  For profiling purposes.
        
    line_count = 0         
    validnumbers_count = 0    
    negative_numbers_count = 0
    
    sum_resultstring = "No selected valid numbers were found."
    message_string =""
    quantized_grand_total = None
    
    get_selections = editor.getSelections()
    
    grand_total = Decimal('0.0')
    
    for sel in range(get_selections):
        start_pos = editor.getSelectionNStart(sel)
        end_pos = editor.getSelectionNEnd(sel)
        text = editor.getTextRange(start_pos, end_pos).strip()
        lines = text.split('\n')
        
        for line in lines:
            line_count  += 1                        
            line_tokens = line.split()
            
            for num_string in line_tokens:            

                if is_potentially_valid_number(num_string):
                    
                    parsed_num = parse_generic_number(num_string)                                     
                    
                    if parsed_num is  None:                        
                        continue 
                        
                    validnumbers_count += 1
                        
                    if parsed_num < 0:
                        negative_numbers_count += 1                
                    
                    # Finally add the number we found and digested. There is a theoretical possibility for overflow 
                    # as sometimes too many borderline large numbers are accepted and added.
                    
                    grand_total += parsed_num           # Addition, everything remains in Decimal type format. 
                
    # Ready to display the results.    
    # Simplify decimal representations if appropriate. Format it with two places after the decimal point unless the input had more mantissa digits.
    
    if DO_PROFILING:
        elapsed_time = (time.time() - start_time) * 1000   # Convert to milliseconds. For profiling purposes.     

    if validnumbers_count > 0:
        grand_total = grand_total.normalize()    #should get rid of trailing zeroes.        
        
        # Convert the grand_total Decimal object to a tuple format (sign, digits, exponent) for easier attribute access and analysis.
        grand_total_tuple = grand_total.as_tuple() 
                        
        # Calculate both the exponent and the total number of digits in grand_total
        exponent_value = grand_total.adjusted()  # Assuming grand_total is a Decimal object
        total_digits = len(grand_total.as_tuple().digits)
        
        try:
            # If both the exponent and the total number of digits are within limits, try to quantize
            if (exponent_value < MAX_PRECISIONDIGITS) and (total_digits < MAX_PRECISIONDIGITS):
                quantized_grand_total = grand_total.quantize(Decimal('0.00'))
        except InvalidOperation:            
            quantized_grand_total = grand_total      # Quantization error, fall back to the original number.
                                         
        # A robust way to check for integers, as it doesn't involve any type conversions.
        is_integer = grand_total_tuple.exponent >=0 
        
        if is_integer:
            sum_resultstring = 'Selected Sum = {}'.format(int(grand_total))  # Integers with or without exponents
        elif quantized_grand_total == grand_total:  
            sum_resultstring = 'Selected Sum = {:.2f}'.format(quantized_grand_total)  # The ONLY place a Decimal is explicitly converted to another type. 
        else:
            sum_resultstring = 'Selected Sum = {}'.format(grand_total)   #  Noninteger. 
    
    if DO_COPY_TO_CLIPBOARD:     
        copy_to_clipboard(sum_resultstring) # Main result.
                        
    message_string = sum_resultstring
    
    if validnumbers_count > 0:
        if EXTRA_NOTIFICATION_INFO:
            message_string += '\nIn all, {} numbers were evaluated and added.'.format(validnumbers_count)
            if (negative_numbers_count > 0):
                message_string += ' \nOf those, {} were negative numbers.'.format(negative_numbers_count)        
                
    notepad.messageBox(message_string)  # Popup window with result and optional extra notifications. 
                 
    if (skipped_due_to_precision > 0) and EXTRA_NOTIFICATION_INFO:
        notepad.messageBox('{} numbers ignored due to digit length exceeding {}'.format(skipped_due_to_precision, ctx.prec), '')
    
    # Display elapsed time for profiling purposes.
    if DO_PROFILING:
        notepad.messageBox("Elapsed Time: {:.2f} ms".format(elapsed_time), "Performance Metrics")      
        print("Elapsed Time: {:.2f} ms".format(elapsed_time))    # Extra logging. Development only.      
    
    
#    if conversion_fail_count > 0:
        #notepad.messageBox('{} numbers ignored due to conversion errors to arbitrary precision Decimal format.'.format(conversion_fail_count)) 
        #print("Numbers ignored : {}".format(conversion_fail_count))  
                
#    print(" {} numbers ignored due to conversion errors to Decimal arbitrary precision library format.".format(conversion_fail_count))     # Extra logging. Development only. 
    
