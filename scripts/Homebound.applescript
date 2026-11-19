-- Homebound.app: a stay-open applet that runs the local server while it's open.
-- Built by scripts/make-app.sh, which replaces @@REPO@@ with the repo path.
property ctl : "@@REPO@@/scripts/homebound-ctl.sh"

on run
	startAndOpen()
end run

on reopen -- clicking the Dock icon while running
	startAndOpen()
end reopen

on startAndOpen()
	try
		do shell script quoted form of ctl & " start"
		open location "http://127.0.0.1:8765"
	on error errMsg
		display dialog "Homebound couldn't start." & return & return & errMsg buttons {"OK"} default button 1 with icon stop with title "Homebound"
	end try
end startAndOpen

on quit
	try
		do shell script quoted form of ctl & " stop"
	end try
	continue quit
end quit
