- [x] in current enrolment, student should be searchable rather than dropdown? course should be searchable too? as the current selection could have over long list and bad UX, or what's the best practice for this?
- [x] in public enrolment page, sort by monday - sunday arrangement, and could it use search2 as list in enrolment to present course selection?
- [] should the student in the class detail, not marked as absent by default? should there be a status for unmarked attendance?
- [] enrolment in student detail page, should it be clickable to go to the enrolment detail page?
- [] transfer all enrolments (in batch) of a course to another course. 


- [x] enrolment list page, should have export funciton, which will export all enrolment details of currently published courses. with enrolmnent status, contacts, student names, course names, etc. so the administrator can chase pending ones and use for roll.

- [x] 
clock in, should extract if the current teacher has classes today, and show the classes in the clock in page. e.g. 1. "you don't have any classes today, you don't need to clock in". and the clock in button is disabled. 
2. "you have the following classes today: xxxx" and the clock in button is enabled. 

clock out only visible if the teacher has clocked in.

if there is a missing clock out record, e.g. this teacher has clocked in, but has not clocked out, and the 2nd day comes, then the clock out button should be visible, and the clock in button for today's class should be disabled first, until clock out is done.

rememebr to detect the distance of the facility from the current location, and only allow clock in if the distance is within reasoanble (system configured) range.

help me review above design, and improve it if needed.

- [] multiple select batch duplicate courses as draft with modal confirmation, with checkbox indicating if existing enrolments should be duplicated as pending as well. and check if all selected courses are all weekly classes. if yes, provide a option to specify the new start date and end date; if no, don't show the option. 

- [] validate the timesheet based on the attendance: 帮我 review 下 timesheet 那边的代码，看是否会有 bug,比如记录错误,记录不上,展示,该有 clock in / out 但是没有(标记老师为 absent),或者有 clock in 但是 没有 clock out,或者其他的问题

- [] in enrolment list page, should be multiple select with filter and with notification function, like in student list page. actually, the logic is exactly the same, the only difference is in enrolment list page, the contacts are extracted from the student info of the enrolment.