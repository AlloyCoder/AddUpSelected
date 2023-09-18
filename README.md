# AddUpSelected

A single-file Python script for Notepad++ that sums up all numbers in a selection. This script is flexible and tolerant of various common number formats.

## Purpose

This script serves as a plug-in for the Notepad++ editor. It is designed to sum up numbers within a selected text range. The script aims to provide a simple and intuitive utility for everyday use. It focuses on:

- Decimal notation
- Negative numbers
- Dollar amounts
- Proper comma-separated thousands-grouping

> **Note**: The script intentionally ignores scientific notation and anything reminiscent of arithmetic. It considers certain characters like `() []` as neutral and valid, which is a subjective choice.

## Features

- **Arbitrary Precision**: Supports up to 200 decimal places by default. This can be changed by modifying the `MAX_PRECISIONDIGITS` constant.
- **Decimal Separator**: Recognizes only the period (`.`) as the decimal separator.
- **Negative Numbers and Dollar Signs**: Capable of handling both.
- **Exponential Notation**: Handles simple forms like `2.5E5`.
- **Filtering**: Filters out numbers with ambiguous formatting or characters.
- **Multiple Negative Signs**: These invalidate a number as the script does not perform arithmetic.

## Installation

1. **Download**: Download the `AddUpSelected.py` file.
2. **Locate PythonScript Folder**: 
    - Go to `Plugins -> Python Script -> New Script` in Notepad++. This will show you the relevant folder.
    - Alternatively, navigate to `C:\Users\[YourUsername]\AppData\Roaming\Notepad++\plugins\config\PythonScript\scripts`.
3. **Move the Script**: Copy the downloaded `AddUpSelected.py` file into the `scripts` folder within the `PythonScript` directory.
4. **Restart Notepad++**: Close and reopen Notepad++.
5. **Verify Installation**: Go to `Menu > Plugins > PythonScript > Scripts`. You should see `AddUpSelected` listed.

## Usage

1. **Select Text**: Select a range of text in Notepad++. Column selections can be particularly useful: drag the mouse cursor over text while pressing `ALT`.
2. **Run the Script**: Navigate to `Menu > Plugins > PythonScript > Scripts > AddUpSelected`.
3. **View Result**: A pop-up window will display the total sum of all numbers in the selected text.
4. **Clipboard**: The sum is also copied to the clipboard in the format: "Selected Sum = 100".

## Additional Notifications

Pop-up notifications will appear if:

- Negative numbers were processed.
- Numbers with too many digits were encountered.

## Notes

This script was inspired by the TextFX number add-up plugin, which was never ported to the 64-bit version of Notepad++.
