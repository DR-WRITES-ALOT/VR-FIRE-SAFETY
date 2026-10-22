using System.Collections.Generic;

/// <summary>
/// All lesson text lives in this one file so the teaching content can be checked
/// and edited without touching the game logic.
///
/// Content is written for a beginner-level college project and follows current
/// Indian fire-safety practice (IS 15683 / IS 2190 conventions) plus recognised
/// first-aid guidance. The sources are listed in <see cref="References"/>.
/// </summary>
public static class LessonContent
{
    public const string Disclaimer =
        "This is a basic educational simulation. It is not a substitute for professional " +
        "fire-safety training, a real evacuation drill, or certified first-aid instruction.";

    // ------------------------------------------------------------------ //
    // Section A - immediate response
    // ------------------------------------------------------------------ //

    public static class SectionA
    {
        public const string IntroTitle = "Section A - Immediate response";
        public const string IntroBody =
            "You are in an office corridor and you see a small fire in a store room.\n\n" +
            "Fire can grow from a small flame to a room full of smoke in a few minutes. " +
            "Your first actions matter more than fighting the fire.\n\n" +
            "<b>In this section you will raise the alarm and learn the correct first response.</b>";

        public const string AlarmObjective = "Walk to the red fire alarm call point and interact (E) to raise the alarm.";

        public const string AlarmRaisedTitle = "Alarm raised";
        public const string AlarmRaisedBody =
            "<b>Good. The alarm warns everyone in the building.</b>\n\n" +
            "Now follow the five immediate actions:\n\n" +
            "1.  <b>Raise the alarm</b> - done.\n" +
            "2.  <b>Alert others</b> only if it is safe to do so. Do not delay your own escape.\n" +
            "3.  <b>Call 112</b> - the all-in-one emergency number in India.\n" +
            "4.  <b>Evacuate promptly</b> and leave your belongings behind.\n" +
            "5.  <b>Avoid smoke and fire.</b> Do not go back inside.";

        public const string PhoneObjective = "Practise the emergency call at the red 112 phone on the wall.";

        public const string PhoneTitle = "Calling 112";
        public const string PhoneBody =
            "<b>Say these things clearly:</b>\n\n" +
            "-  What happened (fire, smoke, explosion)\n" +
            "-  Exact address, building name and floor\n" +
            "-  Whether anyone is trapped or injured\n" +
            "-  Your name and phone number\n\n" +
            "<b>Do not hang up</b> until the operator tells you to. Follow their instructions.\n" +
            "Calling 112 does not replace raising the building alarm.";

        public const string PhoneDoneTitle = "Call made";
        public const string PhoneDoneBody =
            "You reported the fire and gave the building details.\n\n" +
            "Next you will learn what protection masks can and cannot do, and which " +
            "extinguisher is correct for which fire.";
    }

    // ------------------------------------------------------------------ //
    // Section B - masks and extinguishers
    // ------------------------------------------------------------------ //

    public static class SectionB
    {
        public const string MaskObjective = "Find the mask display in the corridor and interact (E) to study it.";

        public const string MaskTitle = "Masks and smoke";
        public const string MaskBody =
            "Smoke from a fire contains <b>carbon monoxide, hydrogen cyanide and other toxic gases</b>.\n\n" +
            "<b>Cloth or surgical mask</b> - no useful protection from fire smoke.\n" +
            "<b>N95 / KN95 respirator</b> - filters particles only. It does <b>not</b> filter carbon monoxide " +
            "or other gases, and it supplies no oxygen.\n" +
            "<b>Certified fire-escape hood</b> - a short-duration escape aid for trained users. It does not " +
            "protect against an oxygen-deficient atmosphere and is never a reason to delay escape.\n" +
            "<b>Firefighter SCBA</b> - a self-contained air supply worn with full protective clothing by " +
            "trained firefighters. Civilians do not use it.";

        public const string MaskRulesTitle = "Never rely on a mask";
        public const string MaskTypesTitle = "Which mask? What it actually does";
        public const string MaskTypesBody =
            "<b>Cloth or surgical mask</b>\n" +
            "Loosely fitting, not sealed to the face. It does not filter carbon monoxide or other " +
            "toxic fire gases, and it gives no useful protection in a fire.\n\n" +
            "<b>N95 / KN95 respirator</b>\n" +
            "Filters fine particles only, and only when it is sealed to a clean-shaven face. It does " +
            "<b>not</b> supply oxygen and does not stop CO, so it is not fire protection.\n\n" +
            "<b>Certified escape hood</b>\n" +
            "A short-duration escape aid with a filter and a hood. It buys minutes of filtered escape " +
            "time and does not protect against oxygen-deficient air. It is not a reason to walk into " +
            "smoke, and it is not a substitute for a clear escape route.\n\n" +
            "<b>SCBA (self-contained breathing apparatus)</b>\n" +
            "Supplies its own air. It is fire-service equipment, worn by trained firefighters with " +
            "full protective clothing - not something to look for during an evacuation.\n\n" +
            "<b>The rule for this building:</b> do not delay evacuation to find any mask, and never " +
            "enter smoke because you are wearing one. Leave by the nearest safe route.";

        public const string MaskRulesBody =
            "-  <b>Never delay evacuation</b> to look for a mask or hood.\n" +
            "-  <b>Never enter a smoke-filled area</b> because you are wearing a mask.\n" +
            "-  A mask does not make toxic smoke safe, and it does not create oxygen.\n" +
            "-  If you are caught in smoke, move away from it and use the nearest safe exit.\n\n" +
            "Firefighters enter burning buildings in breathing apparatus. That is their job, not yours.";

        public const string ExtIntroTitle = "Indian fire classes";
        public const string ExtIntroBody =
            "Indian practice uses these classes of fire:\n\n" +
            "<b>Class A</b> - ordinary solid combustibles: wood, paper, cloth, plastics.\n" +
            "<b>Class B</b> - flammable liquids: petrol, diesel, solvents, paints.\n" +
            "<b>Class C</b> - flammable gases under pressure: LPG, CNG, methane, acetylene.\n" +
            "<b>Class D</b> - combustible metals: magnesium, sodium, potassium.\n" +
            "<b>Class F</b> - cooking oils and fats.\n\n" +
            "<b>Energised electrical equipment</b> is not a separate Indian class. It is a hazard that " +
            "affects which extinguisher you may use - CO2 or dry powder are commonly chosen because they " +
            "do not conduct electricity.";

        public const string ExtSafetyTitle = "Safety rules before you fight a fire";
        public const string ExtSafetyBody =
            "-  <b>Never use water</b> on burning cooking oil or on energised electrical equipment.\n" +
            "-  <b>Do not try to put out a gas fire</b> while gas is still leaking. Raise the alarm and evacuate.\n" +
            "-  <b>Read the label:</b> check the extinguisher type, its rating, the manufacturer's " +
            "instructions and what is actually burning.\n" +
            "-  Use an extinguisher only on a <b>small, contained fire</b>, only if you are trained, the " +
            "alarm has been raised and a <b>safe escape route stays behind you</b>.\n" +
            "-  Never turn your back on a fire and never let it block your exit.";

        public const string ExtObjective = "Inspect all six extinguisher models. Reviewed: 0 of 6.";

        public const string PassTitle = "PASS technique";
        public const string PassBody =
            "<b>P - Pull</b> the safety pin.\n" +
            "<b>A - Aim</b> the nozzle at the base of the fire, not at the flames.\n" +
            "<b>S - Squeeze</b> the handle to discharge.\n" +
            "<b>S - Sweep</b> slowly across the base of the fire until it is out.\n\n" +
            "<b>Stop immediately and evacuate if:</b> the fire does not go out quickly, smoke builds up, " +
            "the fire spreads, or your escape route is threatened. A fire extinguisher is for small, " +
            "contained fires - not for heroics.";

        public const string FireObjective = "Walk to the contained fire demonstration and look at the fire.";

        public const string FireDecisionTitle = "Safe response decision";
        public const string FireDecisionBody =
            "A small fire is burning in a metal bin. The alarm is sounding and the corridor behind you " +
            "is clear.\n\n<b>What is the safe response?</b>";

        public const string DecisionCorrectBody =
            "<b>Correct.</b>\n\n" +
            "The fire is small, it is contained in the metal bin, the alarm has been raised and a clear " +
            "escape route is behind you. This is the only situation in which a trained person may attempt " +
            "to use an extinguisher.\n\n" +
            "If any of those conditions were missing, the correct action is to evacuate.";

        public const string DecisionWrongMaskBody =
            "<b>Not safe.</b>\n\n" +
            "A cloth or N95 mask does not filter toxic gases such as carbon monoxide. Never delay " +
            "evacuation to look for one, and never enter smoke because you are wearing one.\n\n" +
            "The fire is small and contained, the alarm is raised and the escape route is clear, so " +
            "using the extinguisher is the option being demonstrated.";

        public const string DecisionWrongBelongingsBody =
            "<b>Not safe.</b>\n\n" +
            "Never go back for belongings, and never ignore a fire. Seconds matter: fire and smoke " +
            "spread faster than you can collect your things.\n\n" +
            "Try the question again.";

        public const string PassPracticeObjective = "PASS step 1 of 4: interact (E / trigger) with the extinguisher to PULL the pin.";

        public const string PassDoneTitle = "Demonstration complete";
        public const string PassDoneBody =
            "The fire is out.\n\n" +
            "<b>Remember the limits of the demonstration:</b>\n" +
            "-  One extinguisher, one attempt. If the fire is not out, leave immediately.\n" +
            "-  In a real building, the alarm and evacuation come first.\n" +
            "-  Never fight a fire that is growing, spreading, or between you and your exit.\n\n" +
            "Next: the guided evacuation exercise.";
    }

    // ------------------------------------------------------------------ //
    // Section C - evacuation
    // ------------------------------------------------------------------ //

    public static class SectionC
    {
        public const string IntroTitle = "Section C - Evacuation exercise";
        public const string IntroBody =
            "The alarm is sounding. You will now walk the complete escape route:\n\n" +
            "first corridor  ->  one flight of stairs  ->  second corridor  ->  assembly point.\n\n" +
            "Follow the green EXIT signs. Walk, do not run. Keep your escape route clear.";

        public const string StairObjective = "Follow the EXIT signs to the stair lobby at the end of the corridor.";

        public const string LobbyObjective = "In the stair lobby: check the lift, then take the stairs.";

        public const string LiftTitle = "Why not the lift?";
        public const string LiftBody =
            "<b>Lifts are not used during a fire evacuation.</b>\n\n" +
            "-  A lift can stop at the fire floor and open onto smoke or flames.\n" +
            "-  Power can fail and trap you inside.\n" +
            "-  Smoke can enter the lift shaft.\n" +
            "-  Lifts are needed by firefighters and may be recalled automatically.\n\n" +
            "<b>Use the stairs.</b> Hold the handrail, keep to the right and do not run.";

        public const string StairsTitle = "Using the stairs safely";
        public const string StairsBody =
            "-  Hold the handrail and keep to the right.\n" +
            "-  Walk down at a steady pace; do not run or push.\n" +
            "-  Keep moving once you reach the bottom - do not stop in the stairwell.\n" +
            "-  Stairs are the normal escape route in a fire. Lifts are not.";

        public const string SmokeTitle = "Smoke is the real danger";
        public const string SmokeBody =
            "Most fire deaths are caused by smoke inhalation, not burns.\n\n" +
            "-  Smoke is <b>toxic</b>: carbon monoxide makes you confused and sleepy before you notice it.\n" +
            "-  Visibility can drop in seconds and you can become disoriented.\n" +
            "-  <b>Staying low can help you stay below a hot smoke layer, but it is not a guarantee of safety.</b>\n" +
            "-  <b>Never enter dense smoke.</b> Turn around and use a safe route instead.";

        public const string HazardTitle = "Stop - dense smoke ahead";
        public const string HazardBody =
            "Smoke is pouring out of the store room into the corridor. You cannot see through it and " +
            "there are flames inside the room.\n\n" +
            "<b>Do not walk into the smoke.</b>\n\n" +
            "The store room has a fire door. Closing it will contain the smoke and keep the corridor usable.";

        public const string HazardObjective = "Close the store room fire door (E).";

        public const string DoorClosedTitle = "Door closed";
        public const string DoorClosedBody =
            "The fire door is shut. Smoke is contained in the room and the corridor ahead is clear, so " +
            "you can continue to the exit.\n\n" +
            "<b>If the smoke had still blocked your way and there was no other route:</b>\n" +
            "-  Move to a safer location and close doors behind you.\n" +
            "-  Call 112 and tell them where you are.\n" +
            "-  Seal gaps if you can and signal for help from a window.\n" +
            "-  Never re-enter the smoke.";

        public const string ExitObjective = "Continue along the corridor and open the exit doors.";

        public const string OutdoorObjective = "Walk to the green ASSEMBLY POINT sign outside.";

        public const string AssemblyTitle = "Section D - First aid summary";
        public const string AssemblyBody =
            "You have reached the assembly point. In a real evacuation, stay here, report to the " +
            "responsible person and wait for the fire service.\n\n" +
            "<b>Two first-aid topics to finish the training:</b>";

        public const string BurnsTitle = "Burns - first aid";
        public const string BurnsBody =
            "<b>1. Make sure the area is safe</b> before you help.\n" +
            "<b>2. Cool the burn</b> under cool running water for <b>20 minutes</b>, as soon as possible.\n" +
            "<b>3. Remove nearby jewellery and clothing</b> - only if it is not stuck to the skin.\n" +
            "<b>4. Do not apply</b> ice, toothpaste, oil, butter or turmeric.\n" +
            "<b>5. Do not burst blisters.</b>\n" +
            "<b>6. Cover loosely</b> with a clean, non-fluffy dressing after cooling.\n" +
            "<b>7. Seek urgent medical care</b> for severe, extensive, deep or otherwise concerning burns " +
            "(face, hands, feet, joints, or any burn that worries you).";

        public const string SmokeInhalationTitle = "Smoke inhalation - first aid";
        public const string SmokeInhalationBody =
            "<b>Never enter a dangerous area</b> to retrieve a casualty.\n" +
            "Move the person into fresh air <b>only if it is safe to do so</b>.\n" +
            "<b>Call 112</b> and ask for urgent medical assessment.\n" +
            "Monitor their <b>responsiveness and breathing</b>.\n" +
            "If they are unresponsive and not breathing normally, <b>follow the emergency dispatcher's " +
            "instructions</b> for CPR and use an AED if one is available.\n\n" +
            "Smoke inhalation can worsen over hours. Everyone exposed to fire smoke should be assessed " +
            "by a medical professional.";

        public const string CompleteTitle = "Training complete";
        public const string CompleteBody =
            "You completed all four sections:\n\n" +
            "A  Raised the alarm, called 112 and learned the immediate response.\n" +
            "B  Learned what masks cannot do, the extinguisher types and PASS.\n" +
            "C  Evacuated by the stairs to the assembly point and contained a smoke hazard.\n" +
            "D  Reviewed burn and smoke-inhalation first aid.\n\n" +
            "Raise the alarm early, keep your escape route clear, and never enter dense smoke.";
    }

    // ------------------------------------------------------------------ //
    // Extinguisher cards
    // ------------------------------------------------------------------ //

    public class ExtinguisherInfo
    {
        public string Id;
        public string Title;
        public string Body;
        /// <summary>Shown when the player walks up to a unit: which fire classes it is for.</summary>
        public string UseWhen;
        /// <summary>Why this unit is or is not right for the small contained fire in the corridor.</summary>
        public string ForThisFire;
    }

    public static readonly ExtinguisherInfo[] Extinguishers =
    {
        new ExtinguisherInfo
        {
            Id = "ext_water",
            Title = "Water extinguisher",
            UseWhen = "Class A solids such as wood, paper and cloth.",
            ForThisFire = "The bin contains ordinary solids, so water is rated for this fire - but only in a small, "
                       + "contained fire like this one, with a clear exit behind you.",
            Body = "<b>Class A</b> - wood, paper, cloth and similar solid combustibles.\n\n" +
                   "Water cools the burning material. Use only where the label and rating allow it.\n\n" +
                   "<b>Never use water on:</b>\n" +
                   "-  burning cooking oil or fat\n" +
                   "-  energised electrical equipment\n" +
                   "-  flammable liquids"
        },
        new ExtinguisherInfo
        {
            Id = "ext_foam",
            Title = "Foam extinguisher",
            UseWhen = "Class A solids and Class B flammable liquids.",
            ForThisFire = "The bin fire is a solid-fuel fire, so a foam unit rated for Class A can smother it. Foam is "
                       + "the better choice than water if burning liquid were also involved.",
            Body = "<b>Class A and Class B</b>, where the extinguisher is appropriately rated.\n\n" +
                   "Foam blankets the surface of flammable liquids and helps stop re-ignition.\n\n" +
                   "<b>Never use foam on energised electrical equipment</b>, and check the label " +
                   "rating before use."
        },
        new ExtinguisherInfo
        {
            Id = "ext_abc",
            Title = "ABC dry powder extinguisher",
            UseWhen = "Class A, B and C, within the rating on the label.",
            ForThisFire = "ABC powder covers the solid-fuel fire in this bin and is the most common unit in Indian "
                       + "buildings. It makes a mess and reduces visibility, so never use it on a fire you "
                       + "cannot put out quickly.",
            Body = "<b>Class A, B and C</b>, within the rating on the label.\n\n" +
                   "Multi-purpose dry chemical powder is common in Indian buildings because it covers " +
                   "ordinary solids, flammable liquids and flammable gases.\n\n" +
                   "Powder makes a mess and can reduce visibility, and it can damage electronics. " +
                   "Follow the manufacturer's instructions."
        },
        new ExtinguisherInfo
        {
            Id = "ext_co2",
            Title = "CO2 extinguisher",
            UseWhen = "Class B liquids and energised electrical equipment.",
            ForThisFire = "CO2 is the wrong choice for the bin: it is designed for flammable liquids and live "
                       + "electrical equipment, and it can blow burning solids around instead of cooling them.",
            Body = "<b>Class B</b> flammable liquids and <b>energised electrical equipment</b>.\n\n" +
                   "CO2 leaves no residue, which makes it useful near electrical equipment. Energised " +
                   "electrical equipment is a hazard, not a separate Indian fire class.\n\n" +
                   "The nozzle gets extremely cold and CO2 displaces oxygen in small spaces. " +
                   "Ventilate afterwards."
        },
        new ExtinguisherInfo
        {
            Id = "ext_wet",
            Title = "Wet chemical extinguisher",
            UseWhen = "Class F cooking oils and fats - kitchens only.",
            ForThisFire = "Wet chemical is only for cooking oil and fat fires. There is no cooking oil here, so it is "
                       + "not the right unit for this bin.",
            Body = "<b>Class F</b> - cooking oils and fats.\n\n" +
                   "Wet chemical reacts with burning oil to form a soap-like layer that cools the oil " +
                   "and stops re-ignition.\n\n" +
                   "<b>Never use water on burning cooking oil.</b> In a kitchen fire, switch off the heat " +
                   "if it is safe, and raise the alarm."
        },
        new ExtinguisherInfo
        {
            Id = "ext_d",
            Title = "Special Class D powder",
            UseWhen = "Class D combustible metals - specialist industrial risk.",
            ForThisFire = "Class D powder is only for burning metal. Never use it (or any ordinary unit) on a metal "
                       + "fire: this bin fire is ordinary solid fuel, so a Class D unit is not the right choice.",
            Body = "<b>Class D</b> - combustible metals such as magnesium, sodium and potassium.\n\n" +
                   "Only specially rated metal-fire powders are suitable. Water, foam, CO2 and ordinary " +
                   "ABC powder can make a metal fire worse or react violently.\n\n" +
                   "This is a specialist industrial risk: evacuate and call the fire service."
        }
    };

    // ------------------------------------------------------------------ //
    // References
    // ------------------------------------------------------------------ //

    public class Reference
    {
        public string Title;
        public string Publisher;
        public string Url;
    }

    public static readonly Reference[] References =
    {
        new Reference
        {
            Title = "Burns - Fact sheet",
            Publisher = "World Health Organization",
            Url = "https://www.who.int/news-room/fact-sheets/detail/burns"
        },
        new Reference
        {
            Title = "Burns and scalds - Treatment",
            Publisher = "National Health Service (UK)",
            Url = "https://www.nhs.uk/conditions/burns-and-scalds/treatment/"
        },
        new Reference
        {
            Title = "Burns: Types, Symptoms and How to Help",
            Publisher = "American Red Cross",
            Url = "https://www.redcross.org/take-a-class/resources/learn-first-aid/burns"
        },
        new Reference
        {
            Title = "General Respiratory Protection Guidance for Employers and Workers",
            Publisher = "US Occupational Safety and Health Administration (OSHA)",
            Url = "https://www.osha.gov/publications/respiratory_protection_bulletin_2011"
        },
        new Reference
        {
            Title = "Use of smoke escape hoods meeting the ANSI-ISEA standard (interpretation letter)",
            Publisher = "OSHA",
            Url = "https://www.osha.gov/laws-regs/standardinterpretations/2010-08-11-1"
        },
        new Reference
        {
            Title = "Respiratory protection - wildfire respirator FAQ",
            Publisher = "3M (manufacturer guidance)",
            Url = "https://multimedia.3m.com/mws/media/1216501O/respiratory-protection-wildfire-faq.pdf"
        },
        new Reference
        {
            Title = "Pamphlet on classification of fires and types of fire extinguishers",
            Publisher = "Research Designs and Standards Organisation, Indian Railways",
            Url = "https://rdso.indianrailways.gov.in/uploads/Draft%20Pamphlet%20on%20Classification%20of%20Fires%20&%20Types%20of%20Fire%20Extinguishers.pdf"
        },
        new Reference
        {
            Title = "Types of Fire Extinguishers, Classes of Fire and How to Use (IS 15683 / IS 2190)",
            Publisher = "National Institute of Fire Safety, India",
            Url = "https://nifsindia.net/blog/how-to-use-a-fire-extinguisher-your-complete-guide-to-fire-safety/"
        },
        new Reference
        {
            Title = "Emergency Response Support System - 112 India",
            Publisher = "Ministry of Home Affairs, Government of India",
            Url = "https://112.gov.in"
        },
        new Reference
        {
            Title = "CPR and ECC guidelines",
            Publisher = "American Heart Association",
            Url = "https://cpr.heart.org/en/resuscitation-science/cpr-and-ecc-guidelines"
        }
    };
}
