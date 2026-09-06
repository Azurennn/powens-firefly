Output demo.gif

Set FontSize 16
Set Width 1000
Set Height 400
Set TypingSpeed 70ms
Set WaitTimeout 30s

Set Shell "zsh"
Env VHS_RECORDING "1"
Env DEMO_MODE "True"

Hide
Type "source ~/.zshrc"
Enter
Type "clear"
Enter
Wait /❯\s*$/
Show

Sleep 1s

Type "powens-firefly --auto"
Enter

Wait /❯\s*$/

Sleep 4s
