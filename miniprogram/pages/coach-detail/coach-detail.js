const app = getApp()

Page({
  data: {
    coach: null,
    courses: [],
    weekDates: [],
    timeSlots: [],
    selectedCourse: null,
    selectedDate: '',
    selectedTime: '',
    note: '',
    coachId: null
  },

  onLoad: function (options) {
    this.setData({
      coachId: options.id
    })
    this.loadCoachDetail(options.id)
  },

  loadCoachDetail: function (id) {
    app.request({
      url: `/coach/${id}`,
      noAuth: true
    }).then((data) => {
      console.log('教练详情数据:', data)
      const weekDates = data.week_dates || []
      const courses = data.courses || []
      
      const formattedDates = weekDates.map(dateStr => {
        const date = new Date(dateStr)
        const days = ['日', '一', '二', '三', '四', '五', '六']
        return {
          date: dateStr,
          dayText: '周' + days[date.getDay()],
          dateText: (date.getMonth() + 1) + '/' + date.getDate()
        }
      })
      
      const timeSlots = data.time_slots || []
      console.log('timeSlots原始数据:', timeSlots.slice(0, 5))
      console.log('selectedDate:', formattedDates.length > 0 ? formattedDates[0].date : '')
      
      this.setData({
        coach: data.coach,
        courses: courses,
        weekDates: formattedDates,
        timeSlots: timeSlots,
        selectedDate: formattedDates.length > 0 ? formattedDates[0].date : '',
        selectedCourse: courses.length > 0 ? courses[0].id : null
      })
      console.log('设置的timeSlots数量:', this.data.timeSlots.length)
      console.log('设置的selectedDate:', this.data.selectedDate)
    }).catch((err) => {
      wx.showToast({ title: err, icon: 'none' })
    })
  },

  selectCourse: function (e) {
    this.setData({
      selectedCourse: e.currentTarget.dataset.id
    })
  },

  selectDate: function (e) {
    this.setData({
      selectedDate: e.currentTarget.dataset.date,
      selectedTime: ''
    })
  },

  selectTime: function (e) {
    const booked = e.currentTarget.dataset.booked === 'true'
    if (booked) {
      wx.showToast({ title: '该时间段已被预约', icon: 'none' })
      return
    }
    this.setData({
      selectedTime: e.currentTarget.dataset.time
    })
  },

  onNoteInput: function (e) {
    this.setData({
      note: e.detail.value
    })
  },

  getDayText: function (dateStr) {
    if (!dateStr) return ''
    const days = ['日', '一', '二', '三', '四', '五', '六']
    try {
      const date = new Date(dateStr)
      return '周' + days[date.getDay()]
    } catch (e) {
      return ''
    }
  },

  getDateText: function (dateStr) {
    if (!dateStr) return ''
    try {
      const date = new Date(dateStr)
      const month = date.getMonth() + 1
      const day = date.getDate()
      return month + '/' + day
    } catch (e) {
      return ''
    }
  },

  submitBooking: function () {
    if (!this.data.selectedCourse) {
      wx.showToast({ title: '请选择课程', icon: 'none' })
      return
    }
    if (!this.data.selectedTime) {
      wx.showToast({ title: '请选择时间', icon: 'none' })
      return
    }

    app.request({
      url: '/book',
      method: 'POST',
      data: {
        coach_id: this.data.coachId,
        course_id: this.data.selectedCourse,
        date: this.data.selectedDate,
        time_slot: this.data.selectedTime,
        note: this.data.note
      }
    }).then(() => {
      wx.showToast({ title: '预约成功', icon: 'success' })
      setTimeout(() => {
        wx.navigateTo({
          url: '/pages/my-bookings/my-bookings'
        })
      }, 1500)
    }).catch((err) => {
      wx.showToast({ title: err, icon: 'none' })
    })
  },

  goBack: function () {
    wx.navigateBack()
  }
})