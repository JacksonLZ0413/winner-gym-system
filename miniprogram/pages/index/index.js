const app = getApp()

Page({
  data: {
    hotCoaches: [],
    courseCategories: [
      { name: '力量训练', icon: '💪' },
      { name: '有氧运动', icon: '🏃' },
      { name: '瑜伽', icon: '🧘' },
      { name: '普拉提', icon: '🏋️' },
      { name: '运动康复', icon: '⚕️' },
      { name: '功能性训练', icon: '🎯' }
    ]
  },

  onLoad: function () {
    this.loadHotCoaches()
  },

  loadHotCoaches: function () {
    app.request({
      url: '/coaches',
      noAuth: true
    }).then((data) => {
      this.setData({
        hotCoaches: data.slice(0, 3)
      })
    }).catch(() => {
      this.setData({
        hotCoaches: []
      })
    })
  },

  goToCoaches: function () {
    wx.switchTab({
      url: '/pages/coaches/coaches'
    })
  },

  goToBookings: function () {
    wx.navigateTo({
      url: '/pages/my-bookings/my-bookings'
    })
  },

  goToCourses: function () {
    wx.switchTab({
      url: '/pages/coaches/coaches'
    })
  },

  goToCoachDetail: function (e) {
    const id = e.currentTarget.dataset.id
    wx.navigateTo({
      url: `/pages/coach-detail/coach-detail?id=${id}`
    })
  }
})