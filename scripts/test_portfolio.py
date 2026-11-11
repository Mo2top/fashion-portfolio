from pathlib import Path
import json,time,os
from PIL import Image,ImageChops,ImageStat
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'work/browser-qa'
OUT.mkdir(parents=True,exist_ok=True)
URL=os.environ.get('PORTFOLIO_TEST_URL','http://127.0.0.1:4173/')
original=json.loads((ROOT/'src/portfolio.generated.json').read_text());report=[]

STATS='''() => {
    window.motionStats=[];
    let active=null;
    const main=document.querySelector('main');
    const sample=record=>{ const frame=t=>{if(active===record){record.frames.push(t);requestAnimationFrame(frame)}};requestAnimationFrame(frame); };
    new MutationObserver(()=>{
        if(main.dataset.transitioning==='true' && !active){
            active={start:performance.now(),frames:[]}; sample(active);
        } else if(main.dataset.transitioning==='false' && active){
            active.duration=performance.now()-active.start; active.reducedAtFinish=matchMedia('(prefers-reduced-motion: reduce)').matches;
            window.motionStats.push(active); active=null;
        }
    }).observe(main,{attributes:true,attributeFilter:['data-transitioning']});
}'''

def wait_page(page,number):
    page.wait_for_selector(f'main[data-page="{number}"][data-transitioning="false"][aria-busy="false"]')
    page.locator('.portfolio-frame > .original-artwork img').evaluate('(image)=>image.decode()')

with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,**({'executable_path':os.environ['PORTFOLIO_CHROMIUM_PATH']} if os.environ.get('PORTFOLIO_CHROMIUM_PATH') else {}))
    # All pages in both languages: real two-second transitions on desktop/mobile.
    for name,w,h,dpr,mobile in [('desktop',1440,900,1,False),('mobile',390,844,3,True)]:
        context=browser.new_context(viewport={'width':w,'height':h},device_scale_factor=dpr,is_mobile=mobile,has_touch=mobile)
        page=context.new_page();errors=[];bad_responses=[]
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.on('response',lambda response:bad_responses.append(response.url) if response.status>=400 else None)
        page.goto(URL);wait_page(page,1);page.evaluate(STATS)
        assert page.locator('.page-dots button').count()==13
        for language in ['en','zh']:
            if language=='zh':
                page.emulate_media(reduced_motion='reduce');page.keyboard.press('Home');wait_page(page,1)
                page.get_by_role('button',name='中文',exact=True).click()
                page.wait_for_selector('main[data-language="zh"]');wait_page(page,1)
                page.emulate_media(reduced_motion='no-preference')
            assert page.locator('main').get_attribute('data-language')==language
            for number in range(1,14):
                wait_page(page,number)
                current=page.locator('.portfolio-frame > .original-artwork img')
                assert f'/{language}/page-{number:02d}-' in current.evaluate('(image)=>image.currentSrc')
                rect=page.locator('.portfolio-frame').bounding_box()
                assert abs(rect['width']/rect['height']-16/9)<0.005
                assert rect['x']>=-0.1 and rect['x']+rect['width']<=w+0.1
                assert page.evaluate('document.documentElement.scrollWidth===innerWidth')
                if number<13:
                    # Clicking the artwork/margins advances exactly one page.
                    page.locator('main').click(position={'x':30,'y':90})
                    page.wait_for_selector('main[data-transitioning="true"]')
                    if number==1:
                        assert page.locator('.text-fragment').count()>15
                        page.wait_for_timeout(320)
                        movement=page.locator('[data-scene="outgoing"] .text-fragment').evaluate_all('(els)=>els.map(el=>({m:getComputedStyle(el).transform,o:getComputedStyle(el).opacity,b:getComputedStyle(el).filter}))')
                        assert len({m['m'] for m in movement})>8
                        assert any('blur(' in m['b'] and m['b']!='blur(0px)' for m in movement)
                        assert page.locator('[data-scene="outgoing"] .original-artwork').evaluate('(el)=>getComputedStyle(el).opacity')=='0'
                    wait_page(page,number+1)
            # Last page does not wrap or advance beyond the original order.
            page.locator('main').click(position={'x':30,'y':90});assert page.locator('main').get_attribute('data-page')=='13'
            assert page.locator('.page-arrow').nth(1).is_disabled()
            page.locator('.page-arrow').nth(0).click();wait_page(page,12)
            # Arrow keys work even when a navigation control retains focus.
            page.keyboard.press('ArrowLeft');wait_page(page,11)
            print(f'PASS: {name} {language}: all 13 pages, independent motion, back navigation, bounds',flush=True)
        stats=[s for s in page.evaluate('window.motionStats') if not s['reducedAtFinish']]
        durations=[s['duration'] for s in stats]
        assert all(1850<=duration<=2300 for duration in durations),durations
        intervals=[b-a for s in stats for a,b in zip(s['frames'],s['frames'][1:])]
        fps=1000/(sum(intervals)/len(intervals))
        report.append({'viewport':name,'transitions':len(stats),'durationRangeMs':[round(min(durations)),round(max(durations))],'rafAverageFps':round(fps,1),'imageFailures':bad_responses})
        assert not errors,errors;assert not bad_responses,bad_responses
        context.close()

    # Native-resolution pixel fidelity for every resting PDF page, plus instant
    # reduced-motion navigation without any scatter/blur animation.
    context=browser.new_context(viewport={'width':1920,'height':1200},device_scale_factor=2,reduced_motion='reduce')
    page=context.new_page();page.goto(URL);wait_page(page,1)
    for language in ['en','zh']:
        if language=='zh':
            page.get_by_role('button',name='中文',exact=True).click();page.wait_for_selector('main[data-language="zh"]')
            page.keyboard.press('Home');wait_page(page,1)
        for number in range(1,14):
            wait_page(page,number)
            target=OUT/f'verified-rest-{language}-{number:02d}.png'
            page.locator('.portfolio-frame').screenshot(path=str(target))
            source=ROOT/'public'/original['pages'][number-1]['images'][language][-1]['src'].lstrip('/')
            with Image.open(target) as actual_file,Image.open(source) as source_file:
                difference=ImageChops.difference(actual_file.convert('RGB'),source_file.convert('RGB'))
                assert not difference.getbbox(),(language,number,difference.getextrema())
            assert page.locator('.text-fragment').count()==0
            assert page.evaluate('document.getAnimations().length')==0
            if number<13:
                start=time.monotonic();page.keyboard.press('ArrowRight');wait_page(page,number+1)
                assert time.monotonic()-start<1,'Reduced motion unexpectedly waits for animation'
        print(f'PASS: {language}: all 13 resting pages match the original PDF pixels exactly; reduced motion has no animations',flush=True)
    assert page.evaluate('localStorage.getItem("portfolio-language")')=='zh'
    page.reload();page.wait_for_selector('main[data-language="zh"]');wait_page(page,1)
    context.close()

    # Cancel safely when language or reduced-motion preference changes mid-flight.
    context=browser.new_context(viewport={'width':1440,'height':900})
    page=context.new_page();page.goto(URL);wait_page(page,1)
    page.locator('main').click(position={'x':40,'y':100});page.wait_for_selector('main[data-transitioning="true"]')
    page.get_by_role('button',name='中文',exact=True).click()
    page.wait_for_selector('main[data-language="zh"][data-page="2"][data-transitioning="false"][aria-busy="false"]')
    assert page.locator('.text-fragment').count()==0
    page.locator('main').click(position={'x':40,'y':100});page.wait_for_selector('main[data-transitioning="true"]')
    page.emulate_media(reduced_motion='reduce');wait_page(page,3)
    assert page.evaluate('document.getAnimations().length')==0
    print('PASS: language and reduced-motion changes safely settle the current transition',flush=True)
    context.close()

    # Language controls never advance; a quick reversal cancels a cold load.
    context=browser.new_context(viewport={'width':390,'height':844})
    page=context.new_page()
    page.route('**/portfolio/zh/**',lambda route:(time.sleep(0.7),route.continue_()))
    page.goto(URL);wait_page(page,1)
    page.get_by_role('button',name='中文',exact=True).click()
    page.get_by_role('button',name='EN',exact=True).click()
    page.wait_for_timeout(900)
    assert page.locator('main').get_attribute('data-language')=='en'
    assert page.locator('main').get_attribute('data-page')=='1'
    print('PASS: rapid language reversal preserves the page and final language choice',flush=True)
    context.close()

    # Blocked storage and motion-asset failure must leave usable original art.
    context=browser.new_context(viewport={'width':390,'height':844},reduced_motion='reduce')
    context.add_init_script('Object.defineProperty(window,"localStorage",{get(){throw new DOMException("Blocked","SecurityError")}})')
    page=context.new_page();page.goto(URL);wait_page(page,1)
    page.get_by_role('button',name='中文',exact=True).click();page.wait_for_selector('main[data-language="zh"]')
    page.keyboard.press('ArrowRight');wait_page(page,2)
    print('PASS: language and navigation work with storage blocked',flush=True)
    context.close()
    context=browser.new_context(viewport={'width':390,'height':844})
    page=context.new_page();page.route('**/portfolio-motion/**',lambda route:route.abort())
    page.goto(URL);wait_page(page,1)
    page.locator('main').click(position={'x':40,'y':100})
    page.wait_for_selector('.page-error');wait_page(page,1)
    assert page.locator('.original-artwork img').evaluate('(image)=>image.complete&&image.naturalWidth>0')
    page.unroute('**/portfolio-motion/**');page.locator('main').click(position={'x':40,'y':100});wait_page(page,2)
    print('PASS: failed layer requests retain original artwork; retry recovers',flush=True)
    context.close()
    # Touch swipes must not also trigger click-to-advance.
    context=browser.new_context(viewport={'width':390,'height':844},device_scale_factor=3,is_mobile=True,has_touch=True)
    page=context.new_page();page.goto(URL);wait_page(page,1)
    session=context.new_cdp_session(page)
    def swipe(start,end):
        session.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':[{'x':start,'y':420}]})
        for fraction in [0.25,0.5,0.75,1]:
            session.send('Input.dispatchTouchEvent',{'type':'touchMove','touchPoints':[{'x':start+(end-start)*fraction,'y':420}]})
        session.send('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]})
    swipe(310,80);wait_page(page,2)
    page.wait_for_timeout(200)
    assert page.locator('main').get_attribute('data-page')=='2'
    swipe(80,310);wait_page(page,1)
    page.set_viewport_size({'width':844,'height':390})
    rect=page.locator('.portfolio-frame').bounding_box()
    assert abs(rect['width']/rect['height']-16/9)<0.005
    assert rect['y']>=0 and rect['y']+rect['height']<=390
    print('PASS: touch navigation advances once per gesture; landscape preserves original proportions',flush=True)
    context.close()
    browser.close()
(OUT/'browser-results.json').write_text(json.dumps(report,indent=2))
print('COMPLETE:',json.dumps(report),flush=True)
