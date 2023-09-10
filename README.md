# AddUpSelected 
A single-file python script for Notepad++ which adds up all numbers in a selection.  Flexible and tolerant of various common formattings.

 
Purpose:
    This script serves as a plug-in for the Notepad++ editor, designed to sum up numbers within a selected text range.
    It aims to provide a simple and intuitive utility for everyday use, focusing on decimal notation, negative numbers,
    dollar amounts, and proper comma-separated thousands-grouping. Scientific notation is intentionally ignored.
    Anything reminiscent of arithmetic will be ignored and not counted.  Lots of other characters like () [] I consider neutral and valid. And yes this is highly subjective. 

Features:
    - Supports arbitrary precision up to 60 decimal places (set it with getcontext().prec= )
    - Recognizes only the period (".") as the decimal separator.
    - Handles negative numbers and optional dollar signs.
    - Filters out numbers with ambiguous formatting or characters.
    - Multiple negative signs invalidate a number.  We're not doing arithmetic, just removing plausibly neutral characters from numbers,
       like [], (), $, trailing *, etc. See examples below.  
       Trailing asterisks are assumed to be neutral footnote markers, not multiplication signs. 

Installation: 
       Download the AddUpSelected.py file. Locate your Notepad++'s PythonScript Folder:
       Navigate to C:\Users\[YourUsername]\AppData\Roaming\Notepad++\plugins\config\PythonScript\scripts.       
       Move the Script: Copy the downloaded AddUpSelected.py file and paste it into the scripts folder within the PythonScript directory.
       Restart Notepad++: Close and reopen Notepad++.
       Verify Installation: Go to Menu > Plugins > PythonScript > Scripts. You should see AddUpSelected listed. If so, the installation was successful.

Usage:
      Select a range of text in Notepad++. Column selections can be particularly useful for adding up numbers: drag the mouse cursor over text while pressing ALT.
      Navigate to Menu > Plugins > PythonScript > Scripts > AddUpSelected.       
      A pop-up window will display the total sum of all numbers in the selected text.       
      The sum is also copied to the clipboard in the format: "Selected Sum = 100".
      Additional pop-up notifications appear if negative numbers were processed, or numbers with too many digits were encountered in the selection.

Notes:
     Inspired by the TextFX number add-up plugin, which was never ported to the 64-bit version of Notepad++.

    
