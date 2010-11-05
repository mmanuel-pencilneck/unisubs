# Universal Subtitles, universalsubtitles.org
# 
# Copyright (C) 2010 Participatory Culture Foundation
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see 
# http://www.gnu.org/licenses/agpl-3.0.html.

#  Based on: http://www.djangosnippets.org/snippets/73/
#
#  Modified by Sean Reifschneider to be smarter about surrounding page
#  link context.  For usage documentation see:
#
#     http://www.tummy.com/Community/Articles/django-pagination/
from django import forms
from teams.models import Team, TeamMember, TeamVideo, TeamVideoLanguage
from django.utils.translation import ugettext_lazy as _
from utils.validators import MaxFileSizeValidator
from django.conf import settings
from django.forms.models import inlineformset_factory
from videos.types import video_type_registrar, VideoTypeError
from django.core.urlresolvers import resolve
from django.http import Http404
from django.contrib.sites.models import Site
from utils.forms import UniSubURLField
from videos.models import Video
from django.utils.safestring import mark_safe

TeamVideoLanguageFormset = inlineformset_factory(TeamVideo, TeamVideoLanguage, extra=1)

class EditTeamVideoForm(forms.ModelForm):
    
    class Meta:
        model = TeamVideo
        fields = ('title', 'description', 'thumbnail', 'all_languages')
    
    def __init__(self, *args, **kwargs):
        super(EditTeamVideoForm, self).__init__(*args, **kwargs)
        self.fields['all_languages'].widget.attrs['class'] = 'checkbox'

class BaseVideoBoundForm(forms.ModelForm):
    video_url = UniSubURLField(label=_('Video URL'), verify_exists=True, 
        help_text=_("Enter the URL of any compatible video or any video on our site. You can also browse the site and use the 'Add Video to Team' menu."))
    
    def clean_video_url(self):
        video_url = self.cleaned_data['video_url']
        
        if not video_url:
            self.video = None
            return video_url

        host = Site.objects.get_current().domain
        url_start = 'http://'+host
        
        if video_url.startswith(url_start):
            #UniSub URL
            try:
                func, args, kwargs = resolve(video_url.replace(url_start, ''))
                
                if not 'video_id' in kwargs:
                    raise forms.ValidationError(_('This URL does not contain video id.'))
                
                try:
                    self.video = Video.objects.get(video_id=kwargs['video_id'])
                except Video.DoesNotExist:
                    raise forms.ValidationError(_('Videos does not exist.'))
                
            except Http404:
                raise forms.ValidationError(_('Incorrect URL.'))
        else:
            #URL from other site
            try:
                self.video, created = Video.get_or_create_for_url(video_url)
            except VideoTypeError, e:
                raise forms.ValidationError(e)
            
            if not self.video:
                raise forms.ValidationError(mark_safe(_(u"""Universal Subtitles does not support that website or video format.
If you'd like to us to add support for a new site or format, or if you
think there's been some mistake, <a
href="mailto:%s">contact us</a>!""") % settings.FEEDBACK_EMAIL))
             
        return video_url
    
class AddTeamVideoForm(BaseVideoBoundForm):
    
    class Meta:
        model = TeamVideo
        fields = ('video_url', 'title', 'description', 'thumbnail')
        
    def __init__(self, team, *args, **kwargs):
        self.team = team
        super(AddTeamVideoForm, self).__init__(*args, **kwargs)
    
    def clean_video_url(self):
        video_url = super(AddTeamVideoForm, self).clean_video_url()
        
        try:
            tv = TeamVideo.objects.get(team=self.team, video=self.video)
            raise forms.ValidationError(mark_safe(u'Team has this <a href="%s">video</a>' % tv.get_absolute_url()))
        except TeamVideo.DoesNotExist:
            pass
        
        return video_url     
    
    def save(self, commit=True):
        obj = super(AddTeamVideoForm, self).save(False)
        obj.video = self.video
        obj.team = self.team
        commit and obj.save()
        return obj
    
class CreateTeamForm(BaseVideoBoundForm):
    logo = forms.ImageField(validators=[MaxFileSizeValidator(settings.AVATAR_MAX_SIZE)], required=False)
    
    class Meta:
        model = Team
        fields = ('name', 'description', 'logo', 'membership_policy', 'video_policy', 
                  'is_visible', 'video_url')
    
    def __init__(self, *args, **kwargs):
        super(CreateTeamForm, self).__init__(*args, **kwargs)
        self.fields['video_url'].label = _(u'Team intro video URL')
        self.fields['video_url'].required = False
        self.fields['video_url'].help_text = _(u'''You can put an optional video 
on your team homepage that explains what your team is about, to attract volunteers. 
Enter a link to any compatible video, or to any video page on our site.''')
        self.fields['is_visible'].widget.attrs['class'] = 'checkbox'
    
    def save(self, user):
        team = super(CreateTeamForm, self).save(False)
        if self.video:
            team.video = self.video
        team.save()
        TeamMember(team=team, user=user, is_manager=True).save()
        return team
    
class EditTeamForm(CreateTeamForm):
        
    def clean(self):
        if 'logo' in self.cleaned_data and not self.cleaned_data.get('logo'):
            del self.cleaned_data['logo']
        return self.cleaned_data
    
    def save(self):
        team = super(CreateTeamForm, self).save(False)
        if self.video:
            team.video = self.video
        team.save()
        return team    